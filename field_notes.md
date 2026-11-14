When working with `pathlib` you can do this;

```Python

library_path = Path(os.getenv('LIBRARY_PATH')) / 'Alestorm' / "Captain Morgan's Revenge"

```

The additional folders can be added with the slashes. If the folder contains an apostrophy use double quotes.

I have gotten to the point of using the `mutagen` code on a single file and a number of things pipe out at me:
* `releasecountry` is Japan?
* musicbrainz (likely my use of MB Picard) has multiple tags including the track, artist and album ids.
* There is duplication of data and I dont know what will read what. As an example I have `disctotal` & `totaldiscs`.
* The name of the artist is going to be fun. Again you have duplication of data `artists`, `artistsort`, `composer`, `albumartistsort` & `albumartist`. There must be a reason for this.
