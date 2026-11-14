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

so I asked Claude to explain this duplication and it turns out annoyingly there isn't a broadly agreed standard on tag naming conventions. Different applications and different devices can look for different tags. 
What this is going to mean in the future is there is going to need to be some kind of device or programme profile so that the appropriate tags are considered. 
The immediate concern I have though is the future database schema.