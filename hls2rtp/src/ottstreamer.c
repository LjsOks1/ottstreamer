#include <stdio.h>
#include <gst/gst.h>

GST_DEBUG_CATEGORY_STATIC(ottstreamer);
#define GST_CAT_DEFAULT ottstreamer

/* Structure to contain all our information, so we can pass it around */
typedef struct _CustomData
{
  GstElement *pipeline;          /* The pipeline */
  GstElement *souphttpsrc;      /* HLS source */
  GstElement *hlsdemux;         /* HLS Demux */
  GstElement *q1;
  GstElement *tsparse;          /* TS parser */
  GstElement *rtpmp2tpay;       /* RTP payer */
  GstElement *queue;            /* Queue element */
  GstElement *udpsink;          /* Sink element */
  GstBus     *bus;              /* Message Bus */

  GMainLoop *main_loop;         /* GLib's Main Loop */
  gboolean buffering;
  GstState target_state;
} CustomData;

/* playbin flags */

/* Forward definition for the message and keyboard processing functions */
static gboolean handle_message (GstBus * bus, GstMessage * msg,
    CustomData * data);


pad_added_handler(GstElement * src, GstPad * new_pad, CustomData * data)
{
    GstPad *sink_pad = gst_element_get_static_pad(data->q1, "sink");
    GstPadLinkReturn ret;
    GstCaps *new_pad_caps = NULL;
    GstStructure *new_pad_struct = NULL;
    const gchar *new_pad_type = NULL;

    GST_INFO("Received new pad '%s' from '%s'", GST_PAD_NAME(new_pad),
        GST_ELEMENT_NAME(src));

    /* If our converter is already linked, we have nothing to do here */
    if (gst_pad_is_linked(sink_pad)) {
        GST_INFO("We are already linked. Ignoring.");
        goto exit;
    }

    /* Check the new pad's type */
    new_pad_caps = gst_pad_get_current_caps(new_pad);
    new_pad_struct = gst_caps_get_structure(new_pad_caps, 0);
    new_pad_type = gst_structure_get_name(new_pad_struct);

    /* Attempt the link */
    ret = gst_pad_link(new_pad, sink_pad);
    if (GST_PAD_LINK_FAILED(ret)) {
        GST_ERROR("Type is '%s' but link failed.", new_pad_type);
    }
    else {
        GST_INFO("Link succeeded (type '%s').", new_pad_type);
    }

exit:
    /* Unreference the new pad's caps, if we got them */
    if (new_pad_caps != NULL)
        gst_caps_unref(new_pad_caps);

    /* Unreference the sink pad */
    gst_object_unref(sink_pad);
}

GstPadProbeReturn
event_probe(GstPad *pad, GstPadProbeInfo *info, gpointer user_data) {
    GstEvent *event = GST_PAD_PROBE_INFO_EVENT(info);
    GST_TRACE("Got event: %s\n", GST_EVENT_TYPE_NAME(event));

    if (GST_PAD_PROBE_INFO_TYPE(info) & GST_PAD_PROBE_TYPE_EVENT_UPSTREAM) {
        if (GST_EVENT_TYPE(event) == GST_EVENT_QOS) {
            GstQOSType type;
            gdouble proportion;
            GstClockTimeDiff diff;
            GstClockTime timestamp;
            gst_event_parse_qos(event, &type, &proportion, &diff, &timestamp);
            GST_TRACE("QOS Event at %"GST_TIME_FORMAT" Jitter:%"GST_TIME_FORMAT, GST_TIME_ARGS(timestamp), GST_TIME_ARGS(diff));
        }
    }
    return GST_PAD_PROBE_OK;
}
int
main (int argc, char *argv[])
{
  CustomData data;
  GstStateChangeReturn ret;
  gboolean res1,res2,res3;

  /* Initialize GStreamer */
  gst_init (&argc, &argv);
  GST_DEBUG_CATEGORY_INIT(ottstreamer, "ottstreamer", 0, "Let's start streaming....");

/* Create the elements */
    data.pipeline = gst_pipeline_new("ottstreamer");
    data.souphttpsrc = gst_element_factory_make("souphttpsrc", "souphttpsrc");
    data.hlsdemux = gst_element_factory_make("hlsdemux", "hlsdemux");
    data.q1 = gst_element_factory_make("queue2", NULL);
    data.tsparse = gst_element_factory_make("tsparse", "tsparse");
    data.rtpmp2tpay = gst_element_factory_make("rtpmp2tpay", "rtpmp2tpay");
    data.queue = gst_element_factory_make("queue2", "queue2");
    data.udpsink = gst_element_factory_make("udpsink", "udpsink");

    if (!data.pipeline || !data.souphttpsrc || !data.hlsdemux || !data.q1 || 
        !data.tsparse || !data.rtpmp2tpay || !data.queue || !data.udpsink) {
        GST_ERROR("Not all elements could be created.");
        return -1;
    }
    /* Build the pipeline */
    gst_bin_add_many(GST_BIN(data.pipeline), data.souphttpsrc, data.hlsdemux, data.q1, data.tsparse,
        data.rtpmp2tpay, data.queue, data.udpsink, NULL);

    res1 = gst_element_link(data.souphttpsrc, data.hlsdemux);
    res1 = gst_element_link(data.q1, data.tsparse);
    res3 = gst_element_link_pads(data.tsparse, "src", data.rtpmp2tpay, "sink");
    res2 = gst_element_link_many(data.rtpmp2tpay, data.queue, data.udpsink, NULL);
    if ((res1&res2&res3) != TRUE) {
        GST_ERROR("Elements could not be linked.");
        gst_object_unref(data.pipeline);
        return -1;
    }
    /* Connect to the pad-added signal */
    g_signal_connect(data.hlsdemux, "pad-added", G_CALLBACK(pad_added_handler), &data);

    /* Set properties */
    g_object_set(data.souphttpsrc, "location", argv[1], NULL);
    g_object_set(data.hlsdemux, "message-forward", TRUE, NULL);
    g_object_set(data.tsparse, "set-timestamps", TRUE, NULL);
    g_object_set(data.udpsink, "clients", argv[2], NULL);
    g_object_set(data.udpsink, "qos", FALSE, NULL);
    g_object_set(data.queue, "max-size-time", 30000000000,NULL);
    g_object_set(data.queue, "max-size-buffers", 0,NULL);
    g_object_set(data.queue, "max-size-bytes", 0,NULL);
    g_object_set(data.queue, "high-watermark", 0.99,NULL);
    g_object_set(data.queue, "low-watermark",0.01,NULL);
    g_object_set(data.queue, "use-buffering",TRUE,NULL);



    /* Add a bus watch, so we get notified when a message arrives */
    data.bus = gst_element_get_bus(data.pipeline);
    gst_bus_add_watch(data.bus, (GstBusFunc)handle_message, &data);

    /* Add a probe for monitoring QOS events*/
    gst_pad_add_probe(gst_element_get_static_pad(data.rtpmp2tpay, "src"), GST_PAD_PROBE_TYPE_EVENT_UPSTREAM, event_probe, &data, NULL);

    /* Start playing */
    ret = gst_element_set_state(data.pipeline, GST_STATE_PAUSED);
    data.target_state = GST_STATE_PLAYING;
    data.buffering = TRUE;
    if (ret == GST_STATE_CHANGE_FAILURE) {
        GST_ERROR("Unable to set the pipeline to the playing state.");
        gst_object_unref(data.pipeline);
        return -1;
    }

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
                gst_debug_bin_to_dot_file(GST_BIN(data->pipeline),GST_DEBUG_GRAPH_SHOW_VERBOSE, "ottstreamer_graph.dot");
                GST_INFO("Pipeline is in PLAY state.");
            }
        }
    }
    break;
    case GST_MESSAGE_ELEMENT: {
        const GstStructure *s = gst_message_get_structure(msg);
        gboolean ret;
        GST_LOG("Message received from:%s with structure:%s", GST_MESSAGE_SRC_NAME(msg),
            gst_structure_get_name(s));

        if (strcmp(GST_MESSAGE_SRC_NAME(msg), "hlsdemux") == 0) {
            if (strcmp(gst_structure_get_name(s), "adaptive-streaming-statistics") == 0) {
                guint64 size, dur;
                GstClockTime buf;
                ret=gst_structure_get_uint64(s, "fragment-size", &size);
                ret=gst_structure_get_uint64(s, "fragment-download-time", &dur);
                g_object_get(data->queue, "current-level-time", &buf, NULL);
                GST_DEBUG("Downloaded segment: %s  Time:%" GST_TIME_FORMAT ", Buffer:%" GST_TIME_FORMAT, 
                    gst_structure_get_string(s, "uri"), GST_TIME_ARGS(dur),GST_TIME_ARGS(buf));
            }

        }
        else if (strcmp(GST_MESSAGE_SRC_NAME(msg), "souphttpsrc0") == 0) {

        }
        else if (strcmp(GST_MESSAGE_SRC_NAME(msg), "souphttpsrc") == 0) {

        }
        else if (strcmp(GST_MESSAGE_SRC_NAME(msg), "tsparse") == 0) {

        }
        else {
            GST_LOG(gst_structure_to_string(s)); 
        }
        break;
    }
    case GST_MESSAGE_QOS: {
        gint64 jitter;
        gdouble proportion;
        gint quality;
        gst_message_parse_qos_values(msg, &jitter, &proportion, &quality);
        GST_DEBUG("QOS values: Jitter:%i, ideal_rate:%d, quality:%i", jitter, proportion, quality);
        break;
    }
    case GST_MESSAGE_BUFFERING: {
        gint percent;
        gst_message_parse_buffering(msg, &percent);
        if (percent == 100) {
            /* a 100% message means buffering is done */
            data->buffering = FALSE;
            /* if the desired state is playing, go back */
            if (data->target_state == GST_STATE_PLAYING) {
                gst_element_set_state(data->pipeline, GST_STATE_PLAYING);
            }
        }
        else {
            /* buffering busy */
            if (!data->buffering && data->target_state == GST_STATE_PLAYING) {
                /* we were not buffering but PLAYING, PAUSE  the pipeline. */
                gst_element_set_state(data->pipeline, GST_STATE_PAUSED);
            }
            data->buffering = TRUE;
            g_print("\rBuffering....%i percent. ", percent);
            fflush(stdout);
        }
        break;
    }
    default:
        break;
  }

  /* We want to keep receiving messages */
  return TRUE;
}
