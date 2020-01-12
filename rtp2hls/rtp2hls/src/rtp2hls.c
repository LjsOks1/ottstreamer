#include <stdio.h>
#include <gst/gst.h>
#include "playlist.h"
#include <unistd.h>  //Needed by getpid()
#include <glib-unix.h>


GST_DEBUG_CATEGORY_STATIC(rtp2hls);
#define GST_CAT_DEFAULT rtp2hls

/* Comes from gstreamer/gst/gstinfo.c
 * Needed by the custom logging function. */
#if defined (GLIB_SIZEOF_VOID_P) && GLIB_SIZEOF_VOID_P == 8
#define PTR_FMT "%14p"
#else
#define PTR_FMT "%10p"
#endif
#define PID_FMT "%5d"
#define CAT_FMT "%20s %s:%d:%s:%s"


#define MPEGTIME_TO_GSTTIME(t) (((t) * (guint64)100000) / 9)

/* Structure to contain all our information, so we can pass it around */
typedef struct _CustomData
{
    GstElement *pipeline;          /* The pipeline */
    GstElement *filesrc;           
    GstElement *udpsrc;
    GstElement *rtpmp2tdepay;
    GstElement *queue;
    GstElement *tsparse;          /* TS parser */
    GstElement *multifilesink;    /* Sink element */
    GstBus     *bus;              /* Message Bus */
    GMainLoop  *main_loop;         /* GLib's Main Loop */
    guint program_number;
    gchar tsparse_srcpad[20];
    Playlist *playlist;
    gboolean discontinuity;
    gint cue_out;
} CustomData;

/* Variables passed through the command line */

static gchar *source="";
static gchar *base_dir="/ddrive/streams/";
static gchar *channel="";
static guint program_number;
static gchar *url_base="";
static guint playlist_size = 8;
static gchar *segment_name="segment_%05d";
static uint preroll_start=200; //in frames
static uint preroll_end=200; //in frames

static GOptionEntry entries[]=
{
    {"source",'s',0,G_OPTION_ARG_STRING,&source,"Source to use. Can be either an RTP stream or a recorded TS file.",NULL},
    {"base_dir",'b',0,G_OPTION_ARG_STRING,&base_dir,"Base directory to create the segments and the playlist in.",NULL},
    {"channel",'c',0,G_OPTION_ARG_STRING,&channel,"Channel name. Will be appended to the base directory name.",NULL},
    {"program_number",'p',0,G_OPTION_ARG_INT,&program_number,"Program to demux from stream.",NULL}, 
    {"url_base",'u',0,G_OPTION_ARG_STRING,&url_base,"URL to use in the playlist file. Channel will be appended.",NULL},
    {"playlist_size",'l',0,G_OPTION_ARG_INT,&playlist_size,"Size of the playlist.",NULL},
    {"segment_name",'n',0,G_OPTION_ARG_STRING,&segment_name,"Segment filenames.",NULL},
    {"preroll_start",'t',0,G_OPTION_ARG_INT,&preroll_start,"Preroll at start.",NULL},
    {"preroll_end",'e',0,G_OPTION_ARG_INT,&preroll_end,"Preroll at end.",NULL},
   {NULL}
};

/* Forward definition for streamer messages */
static gboolean handle_message(GstBus * bus, GstMessage * msg,
    CustomData * data);

void gst_debug_log_custom (GstDebugCategory*,GstDebugLevel,const gchar*,const gchar*,
        gint,GObject*,GstDebugMessage*,gpointer)  G_GNUC_NO_INSTRUMENT;

gboolean
signal_handler (gpointer user_data)
{
  GMainLoop * loop = (GMainLoop *)user_data;

  GST_ERROR ("Interrupt or Terminate received, stopping main loop...\n");
  g_main_loop_quit (loop);

  return TRUE;
}


/*Just a copy of gst_debug_log_default, only elapsed has been changed. */
void
gst_debug_log_custom (GstDebugCategory * category,
                       GstDebugLevel level,
                       const gchar * file,
                       const gchar * function,
                       gint line,
                       GObject * object,
                       GstDebugMessage * message,
                       gpointer user_data)
{
  gint pid;
  gchar *obj = NULL;
  const gchar *message_str;
  FILE *log_file = user_data ? user_data : stderr;
  GDateTime *now=g_date_time_new_now_local();
  gchar* now_string=g_date_time_format(now,"%Y-%m-%d %H:%M:%S");
  message_str = gst_debug_message_get (message);
  pid = getpid ();

  if (object) {
    /* nicely printed object */
    if (object == NULL) {
        obj= g_strdup ("(NULL)");
    }
    else if(GST_IS_OBJECT (object) && GST_OBJECT_NAME (object)) {
        obj= g_strdup_printf ("<%s>", GST_OBJECT_NAME (object));
    }
    else if (G_IS_OBJECT (object)) {
      obj= g_strdup_printf ("<%s@%p>", G_OBJECT_TYPE_NAME (object), object);
    }
    else {
        obj=g_strdup("(Not recognized)");
    }
  } else {
    obj = (gchar *) "";
  }

    /* no color, all platforms */
#define PRINT_FMT " "PID_FMT" "PTR_FMT" %s "CAT_FMT" %s\n"
  fprintf (log_file, "%s.%06u" PRINT_FMT, now_string,g_date_time_get_microsecond(now),
        pid, g_thread_self (), gst_debug_level_get_name (level),
        gst_debug_category_get_name (category), file, line, function, obj,
        message_str);
  fflush (log_file);
#undef PRINT_FMT
  g_free(now_string);
  g_date_time_unref(now);

  if (object != NULL)
    g_free (obj);
}

GstPadProbeReturn
event_probe(GstPad *pad, GstPadProbeInfo *info, gpointer user_data) {
    GstEvent *event = GST_PAD_PROBE_INFO_EVENT(info);
    CustomData *data = (CustomData*)user_data;
    GST_TRACE("Got event: %s\n", GST_EVENT_TYPE_NAME(event));

    if (GST_PAD_PROBE_INFO_TYPE(info) & GST_PAD_PROBE_TYPE_EVENT_DOWNSTREAM) {
        if (GST_EVENT_TYPE(event) == GST_EVENT_CUSTOM_DOWNSTREAM) {
            const GstStructure *s = gst_event_get_structure(event);
            if (strcmp(gst_structure_get_name(s), "x31-received") == 0) {
                guint64 pts;
                guint gpi;
                gst_structure_get_uint64(s, "PTS", &pts);
                gst_structure_get_uint(s, "GPI", &gpi);
                GST_DEBUG("X31 packet received at PTS:%" GST_TIME_FORMAT ", GPI:0x%0x",
                    GST_TIME_ARGS(MPEGTIME_TO_GSTTIME(pts)), gpi);
                if ((gpi == 0x40) || (gpi == 0x92)) {
                    static guint event_counter;
                    GstStructure *s = gst_structure_new("splice-insert",
                        "splice-event-id", G_TYPE_UINT, 100+event_counter++,
                        "out-of-network-indicator", G_TYPE_BOOLEAN, gpi == 0x40 ? 1 : 0,
                        "pts-time", G_TYPE_UINT64, pts + preroll_start * 3600,
                        "program-number", G_TYPE_UINT, data->program_number, NULL);
                    g_object_set(data->tsparse, "scte35-insert", s, NULL);
                }
                return GST_PAD_PROBE_DROP;
            }
        }
    }
    return GST_PAD_PROBE_PASS;
}

int
main(int argc, char *argv[])
{
    CustomData data;
    GError *error=NULL;
    GOptionContext *context;

    context=g_option_context_new(" - Convert RTP stream to HLS segments with playlist file.");
    g_option_context_add_main_entries(context,entries,NULL);
    if(argc==1) {
        g_print(g_option_context_get_help(context,TRUE,NULL));
        exit(1);
    }
    if(!g_option_context_parse(context,&argc,&argv,&error)) {
        g_print("Parsing options failed! Error:%s\n",error->message);
        exit(1);
    }

    /* Initialize GStreamer */
    gst_init(&argc, &argv);
    gst_debug_add_log_function(gst_debug_log_custom,NULL,NULL);
    gst_debug_remove_log_function(NULL);
    GST_DEBUG_CATEGORY_INIT(rtp2hls, "rtp2hls", 0, "Let's start segmenting....");

    /* check if destination directory exists, create if not */
    if(!g_file_test(g_build_path("/",base_dir,channel,NULL),G_FILE_TEST_IS_DIR)) {
        if(g_mkdir_with_parents(g_build_path("/",base_dir,channel,NULL),0777)<0) {
            GST_ERROR("Destination directory %s couldn't be created.",g_build_path("/",base_dir,channel,NULL));
            exit(-1);
        }
    }
    /* Create the elements & build the pipeline*/
    data.pipeline = gst_pipeline_new("rtp2hls");
    data.tsparse = gst_element_factory_make("tsparse", "tsparse");
    data.multifilesink = gst_element_factory_make("multifilesink", "multifilesink");
    sprintf(data.tsparse_srcpad,"program_%i", program_number);
    data.program_number=program_number;

    if (!data.pipeline || !data.tsparse || !data.multifilesink ) {
        GST_ERROR("Not all elements could be created.");
        return -1;
    }
    gst_bin_add_many(GST_BIN(data.pipeline),data.tsparse,data.multifilesink, NULL);  
    gst_element_link_pads(data.tsparse, data.tsparse_srcpad, data.multifilesink, "sink");

    if(g_strstr_len(source,6,"udp://")==source) {
        data.udpsrc=gst_element_factory_make("udpsrc","udpsrc");
        data.rtpmp2tdepay=gst_element_factory_make("rtpmp2tdepay","rtpmp2tdepay");
        data.queue=gst_element_factory_make("queue","queue");
        if (!data.udpsrc || !data.rtpmp2tdepay || !data.queue ) {
            GST_ERROR("Not all elements could be created.");
            return -1;
        }
        gst_bin_add_many(GST_BIN(data.pipeline),data.udpsrc,data.rtpmp2tdepay,data.queue,NULL);
        g_object_set(data.udpsrc,"uri",source,NULL);
        g_object_set(data.udpsrc,"caps",gst_caps_from_string("application/x-rtp"),NULL);
        gst_element_link_many(data.udpsrc,data.rtpmp2tdepay,data.queue,data.tsparse,NULL);
    } else {
        data.filesrc = gst_element_factory_make("filesrc", "filesrc");
        if (!data.filesrc ) {
            GST_ERROR("Not all elements could be created.");
            return -1;
        }
        gst_bin_add_many(GST_BIN(data.pipeline),data.filesrc,NULL);
        gst_element_link(data.filesrc, data.tsparse);
        g_object_set(data.filesrc, source, NULL);

    }

    /* Set properties */
    g_object_set(data.tsparse, "parse-private-sections", TRUE, NULL);
    g_object_set(data.multifilesink, "next-file", 3, NULL);
    g_object_set(data.multifilesink, "max-file-size", 0, NULL);
    g_object_set(data.multifilesink, "post-messages", TRUE, NULL);
    g_object_set(data.multifilesink, "location", g_build_path("/",base_dir,channel,segment_name,NULL), NULL);
    g_object_set(data.multifilesink, "max-files" , 2000 , NULL);




    /* Add a bus watch, so we get notified when a message arrives */
    data.bus = gst_element_get_bus(data.pipeline);
    gst_bus_add_watch(data.bus, (GstBusFunc)handle_message, &data);

    /* Add a probe for monitoring x31 events*/
    gst_pad_add_probe(gst_element_get_static_pad(data.multifilesink, "sink"), GST_PAD_PROBE_TYPE_EVENT_DOWNSTREAM, event_probe, &data, NULL);

    /* Create the m3u8 playlist*/
    data.playlist = new_playlist(playlist_size, TRUE, g_build_path("/",base_dir,channel,"playlist.m3u8",NULL));
    data.discontinuity = FALSE;
    data.cue_out=0;

    /* Start playing */
    gst_element_set_state(data.pipeline, GST_STATE_PLAYING);
    /* Create a GLib Main Loop and set it to run */
    data.main_loop = g_main_loop_new(NULL, FALSE);
    g_unix_signal_add(SIGINT,signal_handler,data.main_loop);
    g_unix_signal_add(SIGTERM,signal_handler,data.main_loop);
   
    g_main_loop_run(data.main_loop);

    /* Free resources */
    g_main_loop_unref(data.main_loop);
    gst_object_unref(data.bus);
    gst_element_set_state(data.pipeline, GST_STATE_NULL);
    gst_object_unref(data.pipeline);
    return 0;
}

/* Process messages from GStreamer */
static gboolean
handle_message(GstBus * bus, GstMessage * msg, CustomData * data)
{
    GError *err;
    gchar *debug_info;

    switch (GST_MESSAGE_TYPE(msg)) {
    case GST_MESSAGE_ERROR:
        gst_message_parse_error(msg, &err, &debug_info);
        GST_ERROR("Error received from element %s: %s",
            GST_OBJECT_NAME(msg->src), err->message);
        GST_ERROR("Debugging information: %s",
            debug_info ? debug_info : "none");
        g_clear_error(&err);
        g_free(debug_info);
        g_main_loop_quit(data->main_loop);
        break;
    case GST_MESSAGE_EOS:
        GST_INFO("End-Of-Stream reached.");
        g_main_loop_quit(data->main_loop);
        break;
    case GST_MESSAGE_STATE_CHANGED: {
        GstState old_state, new_state, pending_state;
        gst_message_parse_state_changed(msg, &old_state, &new_state,
            &pending_state);
        if (GST_MESSAGE_SRC(msg) == GST_OBJECT(data->pipeline)) {
            if (new_state == GST_STATE_PLAYING) {
                /* Once we are in the playing state, dump dot
                Use dot -Tpng -oimage.png graph_lowlevel.dot to analyze it */
                gst_debug_bin_to_dot_file(GST_BIN(data->pipeline), GST_DEBUG_GRAPH_SHOW_VERBOSE, "rtp2hls_graph.dot");
                GST_INFO("Pipeline is in PLAY state.");
            }
        }
    }
    break;
    case GST_MESSAGE_ELEMENT: {
        const GstStructure *s = gst_message_get_structure(msg);
        GST_LOG("Message received from:%s with structure:%s", GST_MESSAGE_SRC_NAME(msg),
            gst_structure_get_name(s));

        if (strcmp(GST_MESSAGE_SRC_NAME(msg), "tsparse") == 0) {
            if (strcmp(gst_structure_get_name(s), "x31-received") == 0) {
                guint64 pts;
                guint gpi;
                gst_structure_get_uint64(s, "PTS", &pts);
                gst_structure_get_uint(s, "GPI", &gpi);
                GST_DEBUG("X31 packet received at PTS:%" GST_TIME_FORMAT ", GPI:0x%0x",
                    GST_TIME_ARGS(MPEGTIME_TO_GSTTIME(pts)), gpi);
                if ((gpi == 0x40) || (gpi == 0x92)) {
                    data->discontinuity = TRUE;
                }
                if (gpi==0x40) {
                    data->cue_out=1;
                }
                if(gpi==0x92) {
                    data->cue_out=-1;
                }
            }
        } else if (strcmp(GST_MESSAGE_SRC_NAME(msg), "multifilesink") == 0) {
            if (strcmp(gst_structure_get_name(s), "GstMultiFileSink") == 0) {
                int index;
                const gchar *filename;
                GstClockTime duration;
                Playlist_Item *pi;
//                GString *f=g_string_new("");
                gst_structure_get_int(s, "index", &index);
                gst_structure_get_clock_time(s, "timestamp", &duration);
                filename=gst_structure_get_string(s, "filename");
//                GST_DEBUG(gst_structure_to_string(s));
                GST_DEBUG("New file created: filename:%s, Index:%i, Running time:%"GST_TIME_FORMAT " Discontinity:%i",
                    filename, index, GST_TIME_ARGS(duration),data->discontinuity);
//                g_string_printf(f, "http://129.228.120.86/streams/nicktoons_test/%s", filename);
                pi = new_playlist_item(g_build_path("/",url_base,channel,g_path_get_basename(filename),NULL), 
                    15, data->discontinuity,data->cue_out);
                add_segment_to_playlist(data->playlist, pi);
                render_playlist(data->playlist);
                data->discontinuity = FALSE;
                if(data->cue_out>0) {
                    data->cue_out++;
                }
                if(data->cue_out==-1) {
                    data->cue_out=0;
                }
            }
        } else {
            GST_LOG(gst_structure_to_string(s));
        }
        break;
    }
    default:
        break;
    }

    /* We want to keep receiving messages */
    return TRUE;
}
