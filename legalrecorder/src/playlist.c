#include "playlist.h"

Playlist* 
new_playlist(guint max_items, gboolean is_live, gchar *location) {
    Playlist *playlist;
    playlist = g_new(Playlist, 1);
    playlist->max_items = max_items;
    playlist->is_live = is_live;
    playlist->location = g_strdup(location);
    playlist->segments = g_queue_new();
    playlist->first_segment_index = 1;
    return playlist;
}

void 
render_playlist(Playlist *p) {
    GString *content=g_string_new("");
    Playlist_Item *pi;
    content=g_string_append(content, "#EXTM3U\n");
    content = g_string_append(content, "#EXT-X-VERSION:3\n");
    content = g_string_append(content, "#EXT-X-TARGETDURATION:23\n");
    g_string_append_printf(content, "#EXT-X-MEDIA-SEQUENCE:%i\n",p->first_segment_index);
    for (guint i = 0; i < g_queue_get_length(p->segments); i++) {
        pi = g_queue_peek_nth(p->segments,i);
        content=g_string_append(content,"#EXT-X-PROGRAM-DATE-TIME:");
        content=g_string_append(content,g_date_time_format(pi->timestamp,"%Y-%m-%dT%H:%M:%S%:z"));
        content=g_string_append(content,"\n");
        content = g_string_append(content, "#EXTINF:15.000,\n");
        if (pi->discontinuity == TRUE) {
            content = g_string_append(content, "#EXT-X-DISCONTINUITY\n");
        }
        if(pi->cue_out==1) {
            content=g_string_append(content, "#EXT-X-CUE-OUT:240\n");
        }
        if(pi->cue_out>1) {
            g_string_append_printf(content, "#EXT-X-CUE-OUT-CONT:%i/%i\n",(pi->cue_out-1)*15,240);
        }
        if(pi->cue_out==-1) {
            content=g_string_append(content,"#EXT-X-CUE-IN\n");
            pi->cue_out=0;
        }
        g_string_append_printf(content,"%s\n", pi->link);
    }
    if (!p->is_live) {
        content = g_string_append(content, "#EXT-X-ENDLIST\n");
    }
    g_file_set_contents(p->location, content->str, strlen(content->str), NULL);
    g_string_free(content, TRUE);
}

gboolean 
add_segment_to_playlist(Playlist *p, Playlist_Item *i) {
    if (p->segments != NULL) {
        g_queue_push_tail(p->segments, i);
        while (p->max_items > 0 && g_queue_get_length(p->segments) > p->max_items) {
            g_free(g_queue_pop_head(p->segments));
            p->first_segment_index++;
        }
    }
    return TRUE;
}

Playlist_Item*
new_playlist_item(gchar *link, guint duration,gboolean discontinuity,gint cue_out) {
    Playlist_Item *pi;
    pi = g_new(Playlist_Item, 1);
    pi->link = g_strdup(link);
    pi->duration = duration;
    pi->discontinuity = discontinuity;
    pi->cue_out=cue_out;
    pi->timestamp=g_date_time_new_now_local();
    return pi;
}
