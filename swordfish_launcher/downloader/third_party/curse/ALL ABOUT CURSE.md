I've found the various attempts at unofficial documentation of CurseForge/Twitch launcher's internal APIs scattered
 throughout the internet somewhat lacking.  The documentation at https://twitchappapi.docs.apiary.io/, which is the
  best resource I've found so far, lists only the valid API calls and the raw JSON data they return, with no
   indication of what the API calls do or what the data returned means beyond their names.  I set out to correct this.

Unfortunately, the above URL is now either defunct or private.  It appears Curse/Overwolf really don't want people
using their modpacks in launchers other than theirs.  However, with all due respect, their launcher sucks balls, and if
they haven't sopped MultiMC from being able to download Curseforge packs, they won't stop me either.  To that end, a
quick search for "twitchappapi" reveals https://github.com/Gaz492/CurseforgeAPI, which contains an Apiary .apib file,
and https://github.com/SSouper/TwitchAppAPIWrapper, which is a Javascript API wrapper.  I have archived the former in
the project root (minefish) as "curseforge.apib" should the curse of Curse (by which I of course mean the lawyers of
Curse) come after both of these.  I also have a second copy of the same file in the same directory as this Markdown
document should clumsy future-me delete the first one.

For the most part, everything is self explanatory.





On the distinction between media.forgecdn.net and edge.forgecdn.net
-

If one visits the HTML site at curseforge.com and downloads a mod with file ID 1234567, they will receive a download
 link to https://media.forgecdn.net/123/4567/filename.jar.  If one makes the same query to the JSON API, they will
  receive a link to https://edge.forgecdn.net/123/4567/filename.jar.  The only difference I have noticed thus far
   between these two is that media.forgecdn.net sends all of the headers a browser would expect, like Content-Type,
   Content-Length, Last-Modified, Server, Cache-Control, etc., etc.  Since automated scripts don't care about that,
   Curseforge figured "why waste bandwidth sending them?", and edge.forgecdn.net sends the bare minimum headers
    ('Connection', 'Date', and 'Location').