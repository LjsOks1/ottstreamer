#pragma once

#include<glib.h>

struct _Playlist_Item {
    gchar *link;
    guint duration;
    gboolean discontinuity;
};
typedef struct _Playlist_Item Playlist_Item;

typedef struct _Playlist{
    GQueue *segments;
    guint max_items;
    gboolean is_live;
    gchar *location;
    guint first_segment_index;
};
typedef struct _Playlist Playlist;

Playlist*
new_playlist(guint max_items, gboolean is_live, gchar *location);

Playlist_Item*
new_playlist_item(gchar *link, guint duration, gboolean discontinuity);

gboolean
add_segment_to_playlist(Playlist *p, Playlist_Item *i);

void
render_playlist(Playlist *p);