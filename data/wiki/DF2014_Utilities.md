# DF2014:Utilities

120px|rightA collection of third-party **Utilities** that are useful for *Dwarf Fortress* players and modders alike, of which this page serves as a list. *Dwarf Fortress* is a difficult game to play, and any help that can be had in the task is welcome help. 

If you would like to add an article on a *specific* game utility to the wiki, please do so under the <span class="plainlinks">Utility namespace. 
Not included on this page: tileset repositories and graphics set repositories, due to having been given their own, separate pages. Mods have also been listed under their own <span class="plainlinks">Modification namespace. 

To avoid namespace clutter, websites *are* considered utilities and have been included.

A subsection of the Bay12 forums is devoted to such third-party programs, and contains development threads for most of them.

The Lazy Newb Pack is an effort to make *Dwarf Fortress* more accessible for new players or returning veterans by bundling and configuring utilities, graphics and tilesets, and extras such as reference material or more intuitive controls.

1. Launchers

1. Starter Pack

thumb|100x170px|The original LNP launcher
A starter pack is a compilation of tools, tilesets, a launcher, and the game itself. It allows you to start playing DF really quickly on a new machine - no need to download all the latest stuff, check dependencies, and integrate - or even know what you need to get. Packs that include DFHack also include third-party fixes for some bugs, enabled automatically, and significant user interface improvements. The launcher makes changing settings or graphics options much easier (press button, instead of editing files) and can even remember to launch selected utilities whenever you open a game of *Dwarf Fortress*. See Where do I get a Pack? for a list.

1. PyLNP
A cross-platform LNP port, written in Python. The current launcher and configuration interface in starter packs. See PyLNP: The modern cross platform launcher for more information.
- Links: , Releases (for pack maintainers), GitHub Repository, Documentation

1. Manila Launcher (obsolete)
A Java interface that allows easy option toggling, update and devlog checking, and tileset, mod and color scheme switching.  Designed for players who prefer vanilla DF to a bundle like the above. Has not been updated since 2014.
- Links: 

1. 3D Visualizers
1. Stonesense
left|frameless|200px|none
Stonesense is a third party visualizer, implemented as a DFHack plugin, that lets you view your fortress in a classic isometric perspective. It runs alongside *Dwarf Fortress*, and can follow the main game's view, updating in real-time. It is included in DFHack, and can be opened by typing `stonesense` or `ssense` into the console window.

- Links: Utility:Stonesense

1. Armok Vision
left|frameless|200px|none
Armok Vision is a 3D real-time visualizer using Unity. It works as a separate program communicating with the game through fast network interfaces provided by DFHack.

- Links: , GitHub Repository, Discord, Patreon

1. Isoworld
left|frameless|200px|none
Isoworld is an isometric world map viewer, which can display each of the detailed maps exported from Legends mode. It also has a pictographic view which makes finding waterfalls easy.  

Isoworld can link with DFHack to display a game view at full spatial resolution in wider context, including tracking the player's view.  This is particularly useful for adventure mode. The isoworldremote plugin required for this is included with DFHack.

- Links: , GitHub Repository 

1. Voxel Fortress
left|frameless|200px|none
Voxel Fortress converts DF worlds to a voxel format. It takes an export of one of the two elevation maps (for the voxels coordinates), and any other one (for the colors).

The map is saved in .xraw format. An additional utility (e.g. MagicaVoxel Viewer) is required to see the voxel representation of the map.

- Links: , GitHub Repository (includes some instructions)

1. Music and Sounds
1. SoundSense

left|frameless|100px
SoundSense parses game logs and plays reacts to game events with sound effects, incidental music and dwarfy comments. Due to it being written in Java, Soundsense is portable to all platforms.

Note that older Soundsense users may have different default seasonal soundtracks, which were removed and replaced in early 2011. These are available here.

- Links: Website, , Google Code Repository

1. SoundCenSe
left|frameless|100px|
A C# port of SoundSense, it uses the existing sound pack files and XMLs present in SoundSense, but with some added enhancements. More information regarding what specific type of enhancements and how to install SoundCenSe can be gathered at the official forum thread. If problems emerge while trying to get SoundSense to work with the latest versions of Java, this port may prove to be a useful alternative.

- Links: , Releases, GitHub Repository

1. SoundSense-RS
left|frameless|100px|
A SoundSense alternative in Rust with a minimalistic GUI. Sound volumes can be adjusted realtime, based on channel. Events can be ignored with a custom list based on log patterns.

- Links: , Releases, GitHub Repository

1. Game manipulation tools
1. DFHack

left|frameless|200px| 
DFHack is an advanced *Dwarf Fortress* memory access library and a set of tools and scripts using this library, providing direct object-oriented access to Dwarf Fortress's internals as if it were compiled into the game itself. Runs on Windows, Linux, and OS X. The standard configuration enables a variety of included bugfixes and interface upgrades, and provides many useful tools such as "clean all". See main page for a summary of features, common use, and more.
- Links: , Documentation, Releases, GitHub Repository

1. Dwarf Therapist

left|frameless|200px|
Dwarf Therapist gives you an advanced GUI to manage and check dwarf job allocations, military assignments, statistics (such as attributes, personality traits and happiness), sort dwarves by various criteria (e.g. profession, migration wave, happiness, number of assigned jobs etc.) and generally manage the Dwarven Resources of your fortress in a very convenient way. Available for Windows, Mac and GNU + Linux and included in most starter packs.  
- Links: , Releases, GitHub Repository, Manual (outdated)

1. Modding tools
1. Rubble

A useful plugin-based modding tool that generates raws and supports easy installation of reactions, tilesets, macros, modding fixes and DFHack scripts. It is a fork of the now abandoned Blast. Binaries are available for Linux 32-bits, OS X 32-bits and Windows 64-bits, as well as the source (written in Go with building instructions). As of 4.0, a GUI is available for Windows.

1. PyDwarf

For players, PyDwarf is an easy way to manage and configure preferred mods in a way that avoids almost entirely the problems of outdated mods or incompatible groups of mods. For modders, PyDwarf's mod manager exposes a powerful Python API for interacting with raws and other data files.

1. Raw Explorer
A tree-based raw files browser, editor and manager.

1. Dwarf_RAW
A GUI for editing raw files, updated 2019.

1. Dwarf Fortress real-life material helper
A Python script that generates raws based on custom real-life material values.

1. Roses' Random Creature Script
A Python script that generates random creature raws.

1. DF Diagnosipack
A collection of modding tools, with a focus on diagnosing problems and getting statistics on what is found within the raws.
It includes:
- DF Duplisearch - checks your raws folder for duplicated objects, and counts the number of objects of each type (creature, entity, reaction, etc.).
- DF Creatureclasser - tells you what creature classes are in your raws, and what they are used for.
- DF CVunpack - unpacks creature variations, so you can see how the raws for e.g. wolf men really look (spoiler: they have 7 fingers).
- DF Creaturescale - calculates creature weights, and the proportions of each body part and tissue.
- DF Biomeviewer - shows what creature/plants can be found in which biomes.
- DF Rawminer - extracts procedurally generated raws (of Forgotten Beasts etc.) from save files.

1. DF RAW Language server
Modding support for DF RAW files in IDE/Code/Text editors.
Checks syntax of files, detects errors and syntax highlighting.

Current extensions:
- VS Code
- (more are coming)

The Language server is a shared component that can be used to easily add support for more IDE's.

1. World Map / World Gen tools
1. Perfect World DF
Requires an additional (tiny) download to be functional for current versions (40.#): WorldGen.xml .  Easy access to world settings for quick modification to allow highly customized world generation far easier and faster than DF's ingame advanced map maker.  forum thread

1. Fortress World Generator
A bash script for automating world generation of large numbers of worlds on GNU/Linux.

1. Dwarf Map Maker
A Photoshop action script which turns legends mode exported maps into a much prettier fantasy map.  There is also a version available for GIMP.

1. Satellite Map Maker
A GIMP script based on the Dwarf Map Maker that creates a satellite image of *Dwarf Fortress* world maps.

1. Armap
A python script that creates a hand-drawn style map from exported legends world maps.

1. Legends tools
1. Legends Viewer
border|200x200px|left
Legends Viewer loads up the legends you can export in a much more usable format than the Legends mode of DF itself.  Legends Viewer can open pages in new tabs, filter information on a wide range of criteria, and display information on the map as well. Binaries are only available for Windows, as well as the source (written in C#).

- Bay12 Forums thread for current branch for 0.47.XX version of DF, original Branch from 2014

1. World Viewer
border|200x200px|left
An alternative to Legends Viewer that, most specifically, features a timeline of historical events. Binaries are only available for Windows, as well as the source (written in C#). Last updated in late 2017.

- Links: bay12forums 

1. Uristmaps
border|200x200px|left
A web-based interface that displays worlds in the way of an interactive map complete with features and structures.

Links: Website

1. Legends Browser
border|200x200px|left
A web-based multi-platform (Win, Linux, OSX) Viewer. It displays an interactive map and legends information (using legends_plus.xml generated via DFHack).

- links: bay12forums

1. DF Storyteller
border|200x200px|left
Dwarf Fortress Storyteller (DF Storyteller, DF ST) is an application that parses *Dwarf Fortress* legends files, stores them internally and makes them queryable using API's. (Cross platform: Windows, Linux, macOS) This utility can be used to easily create new visualizers to view the legends data. 

- links: Website, Gitlab project, list of visualizers can be found here. An example of a visualizer is The Bard created in DF ST.

1. Remote playing tools

1. Dfterm3

Dfterm3 is a remote *Dwarf Fortress*-playing software for multiple users through a web interface. DFterm3 enables play through a web interface, and games can also be viewed on mobile - or even played if a bluetooth keyboard is attached.  The web interface should work with Chrome or Firefox browsers, but there are known problems using Internet Explorer. DFTerm3 functions via a DFHack plugin, and is thus dependent on each version of DFHack.

It is a successor to dfterm2, which functions similarly using telnet instead of a web browser. This utility only works with version 0.34.11 or earlier.

1. Webfort
thumb|200px|none|Playable in Mac browser.
A newer alternative to dfterm3 that functions similarly, but players must wait in a queue before assuming control for a given period of time. It also functions via a DFHack plugin. Binaries are available for Windows, as well as the source (written in C++).  *(Note: main repo unmaintained.  New repo last updated 5/22/2015.)*

1. DorfServer
thumb|200px|none|Like Twitch, without Twitch.
A remote SSH-based *Dwarf Fortress* host software.  (repo)

1. DFEverywhere

A utility that connects a locally-run *Dwarf Fortress* instance to a proprietary remote website, allowing remote browser-based play. *(Note: Main website no longer available.  Client source here.)*

1. Dwarf Fortress Remote

iOS app (paid) that allows one to play *Dwarf Fortress* remotely with native UI. A server can be set up at home, or on DigitalOcean, AWS or other hosting service.

1. DFPlex 

DFPlex is a plugin for DFHack which introduces simultaneous, real-time online co-op to fortress mode: each player has their own independent view, cursor, menus, etc. so nobody has to wrestle for control. It's a fork of webfort, so players join just by connecting from their web browser.

1. Box64

Box64 allows Dwarf Fortress to be run locally on Android devices. A more detailed tutorial is available here.

1. Language tools

1. DFLang
A language creating tool.

1. Toadese Language Utility
A language editing and translating tool.

1. DFlangOpt
A little tool meant to prevent redundancy when importing or updating language files.

1. Python language extraction and injection script
This simple script will extract words from language files and put them a word per line, for easy automatic translation or treatment. It can also read that list and put the translated words back in their place.

1. Announcement tools

1. DF Assistant 

Game events are split between advisors, each responsible for a separate aspect of your fortress:
- Chief Advisor: keeps track of only the most important events that you don't want to miss
- Military Advisor: combat injuries, deaths, big fights, etc
- Engineering Advisor: building, maintenance, material shortages, etc
- Creature Advisor: anything that lives in and around your fortress, what they think, how they feel, etc.
- Miscellaneous Advisor: rest of the events, like weather, trading, thievery, etc.

Also has configurable sound effects and a bunch of thematic music!

1. DFMon

An announcement monitoring/filtering program, useful to hide some types of job cancellation spam or other more advanced filtering. Note that you can set the game to announce no job cancellations *without* any utilities or mods from the rders menu, with .

1. DF Announcement Filter

An alternative to DFMon written in Java (and thus portable to Linux and OS X).

1. Announcement Window+

Announcement Window+ is a Python application that interfaces with *Dwarf Fortress* to print announcements and combat reports to a separate window. It was written to fix some annoying bugs that are present in DF Announcement Filter, which is no longer being updated.

thumb|300px|none|One less game-pausing hotkey.

1. Filesharing websites

1. Dwarf Fortress File Depot
The Dwarf Fortress File Upload Service - an excellent place to store mods, community games, tilesets and other files. Courtesy of Janus; for files related to *Dwarf Fortress* only.

1. Dwarf Fortress Map Archive

The Dwarf Fortress Map Archive is a large collection of user-submitted maps and videos and a nice flash viewer for perusing them. Maps are uploaded, stored, and downloaded in a special compressed format created by the DF Map Compressor; videos are stored in a compressed version of Toady One's own video-recording format.

Read more about the DF Map Archive on Markavian's User page.

1. Other/miscellaneous

1. DF Map Compressor
thumb|200px|none|Main program window.
The DF Map Compressor encodes multiple bitmaps exported from *Dwarf Fortress* into a single, very compressed, .fdf-map file. The fdf-map file can then be shared with your friends by uploading to the DF Map Archive.

1. Exita
Exita is a Python program that takes your DF world map exports and dump them into several different text outputs.

1. DwarfFamily
A tool that lets you import your legends XML file and converts all dwarf entries to a .GED file, which you can use in Family Tree programs like MyHeritage to display a family tree for the dwarves.

1. Dwarf Fortress News - Android App
Watches the *Dwarf Fortress* devblog. Receives Push Notifications on new updates.

1. DF2HTML
Converts DF screenshots into formatted HTML.

- 
ru:Utilities
