#include <stdio.h>
#include <gst/gst.h>
#include "playlist.h"

GST_DEBUG_CATEGORY_STATIC(rtp2hls);
#define GST_CAT_DEFAULT rtp2hls

#define MPEGTIME_TO_GSTTIME(t) (((t) * (guint64)100000) / 9)

/* Structure to contain all our information, so we can pass it around */
typedef struct _CustomData
{
    GstElement *pipeline;          /* The pipeline */
    GstElement *filesrc;           
    GstElement *tsparse;          /* TS parser */
    GstElement *multifilesink;    /* Sink element */
    GstBus     *bus;              /* Message Bus */
    GMainLoop  *main_loop;         /* GLib's Main Loop */
    guint program_number;
    Playlist *playlist;
    gboolean discontinuity;
} CustomData;

/* playbin flags */

/* Forward definition for the message and keyboard processing functions */
static gboolean handle_message(GstBus * bus, GstMessage * msg,
    CustomData * data);

GstPadProbeReturn
event_probe(GstPad *pad, GstPadProbeInfo *info, gpointer user_data) {
    GstEvent *event = GST_PAD_PROBE_INFO_EVENT(info);
    CustomData *data = (CustomData*)user_data;
    GST_TRACE("Got event: %s\n", GST_EVENT_TYPE_NAME(event));

    if (GST_PAD_PROBE_INFO_TYPE(info) & GST_PAD_PROBE_TYPE_EVENT_DOWNSTREAM) {
        if (GST_EVENT_TYPE(event) == GST_EVENT_CUSTOM_DOWNSTREAM) {
            GstStructure *s = gst_event_get_structure(event);
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
                        "pts-time", G_TYPE_UINT64, pts + 8 * 90000,
                        "program-number", G_TYPE_UINT, data->program_number, NULL);
                    g_object_set(data->tsparse, "scte35-insert", s, NULL);
                    data->discontinuity = TRUE;
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

    /* Initialize GStreamer */
    gst_init(&argc, &argv);
    GST_DEBUG_CATEGORY_INIT(rtp2hls, "rtp2hls", 0, "Let's start segmenting....");

    /* Create the elements */
    data.pipeline = gst_pipeline_new("rtp2hls");
    data.filesrc = gst_element_factory_make("filesrc", "filesrc");
    data.tsparse = gst_element_factory_make("tsparse", "tsparse");
    data.multifilesink = gst_element_factory_make("multifilesink", "multifilesink");
    data.program_number = 14;

    if (!data.pipeline || !data.filesrc || !data.tsparse || !data.multifilesink ) {
        GST_ERROR("Not all elements could be created.");
        return -1;
    }
    /* Build the pipeline */
    gst_bin_add_many(GST_BIN(data.pipeline), data.filesrc, data.tsparse,data.multifilesink, NULL);
    
    gst_element_link(data.filesrc, data.tsparse);
    gst_element_link_pads(data.tsparse, "program_14", data.multifilesink, "sink");


    /* Set properties */
    g_object_set(data.filesrc, "location", "..\\..\\streams\\nicktoons.ts", NULL);
    g_object_set(data.tsparse, "parse-private-sections", TRUE, NULL);
    g_object_set(data.multifilesink, "next-file", 3, NULL);
    g_object_set(data.multifilesink, "max-file-size", 0, NULL);
    g_object_set(data.multifilesink, "post-messages", TRUE, NULL);
    g_object_set(data.multifilesink, "location", "%05d.ts", NULL);



    /* Add a bus watch, so we get notified when a message arrives */
    data.bus = gst_element_get_bus(data.pipeline);
    gst_bus_add_watch(data.bus, (GstBusFunc)handle_message, &data);

    /* Add a probe for monitoring x31 events*/
    gst_pad_add_probe(gst_element_get_static_pad(data.multifilesink, "sink"), GST_PAD_PROBE_TYPE_EVENT_DOWNSTREAM, event_probe, &data, NULL);

    /* Create the m3u8 playlist*/
    data.playlist = new_playlist(0, FALSE, "playlist.m3u8");
    data.discontinuity = FALSE;

    /* Start playing */
    gst_element_set_state(data.pipeline, GST_STATE_PLAYING);
    /* Create a GLib Main Loop and set it to run */
    data.main_loop = g_main_loop_new(NULL, FALSE);
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
                gst_debug_bin_to_dot_file(GST_BIN(data->pipeline), GST_DEBUG_GRAPH_SHOW_VERBOSE, "ottstreamer_graph.dot");
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
/*                guint64 pts;
                guint gpi;
                gst_structure_get_uint64(s, "PTS", &pts);
                gst_structure_get_uint(s, "GPI", &gpi);
                GST_DEBUG("X31 packet received at PTS:%" GST_TIME_FORMAT ", GPI:0x%0x",
                    GST_TIME_ARGS(MPEGTIME_TO_GSTTIME(pts)), gpi);
                if ((gpi == 0x40) || (gpi == 0x92)) {
                    static guint event_counter;
                    GstStructure *s = gst_structure_new("splice-insert",
                        "splice-event-id",G_TYPE_UINT,event_counter++,
                        "out-of-network-indicator",G_TYPE_BOOLEAN,gpi==0x40 ? 1 : 0,
                        "pts-time",G_TYPE_UINT64,pts+8*90000,
                        "program-number",G_TYPE_UINT,data->program_number,NULL);
                    g_object_set(data->tsparse, "scte35-insert", s, NULL);
                    data->discontinuity = TRUE;
                }
  */          }
        } else if (strcmp(GST_MESSAGE_SRC_NAME(msg), "multifilesink") == 0) {
            if (strcmp(gst_structure_get_name(s), "GstMultiFileSink") == 0) {
                int index;
                const gchar *filename;
                GstClockTime duration;
                Playlist_Item *pi;
                GString *f=g_string_new("");
                gst_structure_get_int(s, "index", &index);
                gst_structure_get_clock_time(s, "timestamp", &duration);
                filename=gst_structure_get_string(s, "filename");

                GST_DEBUG("New file created: filename:%s, Index:%i, Running time:%"GST_TIME_FORMAT,
                    filename, index, GST_TIME_ARGS(duration));
                g_string_printf(f, "http://127.0.0.1:8000/%s", filename);
                pi = new_playlist_item(f->str, 15, data->discontinuity);
                add_segment_to_playlist(data->playlist, pi);
                render_playlist(data->playlist);
                data->discontinuity = FALSE;
                g_string_free(f,TRUE);
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
