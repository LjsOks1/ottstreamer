# playlist_localizer

Simple tool to replace segments marked with the #EXT-X-CUE-OUT-CONT tag in the source manifest file with some local segments. Source manifest is not modified, localized manifest file is created into a different folder. Business logic is compiled in, there is not too much to configure from the command line.

Usage:
`playlist_localizer.py src_manifest localised_manifest > logs/localizer_<channel>.log &`

Assumptions/Restrictions:
1. The duration of the localized manifest file is kept on the same duration like the original one. This requires that every segment in the original manifest is marked with the #EXT-X-PROGRAM-DATE-TIME tag.
2. Local segments are copied over to the localized manifest from a playlist stored on a predefined location in the filesystem. The location is:
    `localized_manifest/commercials/playlists/<date>/<break_number>/playlist.m3u8` where:
`date` is the broadcast date between 6am and next 6am.
`break_number` is decided based on the #EXT-X-PROGRAM-DATE-TIME tag of the first segment that has to be replaced. For this there is a daily schedule file needed in the `/localized_manifest/commercials/playlists/YYYY-MM-DD` folder with a fixed name.

3. Local segment insertion is triggered by the #EXT-X-DISCONTINUITY and #EXT-X-CUE-OUT-CONT flags in the regional playlist.

4. It is good practice to add the logs directory to the logrotate config.
