# TranscendentRenovation Solution
### Author: VivisGhost

In order to solve this challenge players need to use a tool like JLECMD to parse Jump Lists. Additionally they will
need to analyze the JumpLists with a tool like a hexeditor.  This challenge is designed to highlight additional 
artifacts of forensic value ignored by popular tools.


What file format is a Jump List stored in? (`Format: *** **`)

This can be found by doing some research and finding a 2016 Zimmerman blog which he called this file format
`OLE CF`. Could be a `CFBF`, format in question should prevent confusion.

A: OLE CF


Which automaticDestinations file contains the `NoNeedToWonder` entry?

This can be found with a simple grep. 

A: f01b4d95cf55d32a.automaticDestinations-ms (`Format: ****************.*********************-**`)


What share path found in the file?

This can be found using Zimmerman's JLECMD tool. It is found at entry 69.

A: `\\tsclient\HauntedHouse`


Which stream holds the `NoNeedToWonder` rename evidence?

Can use a tool like pythons olefile library to parse the streams.

A: 46


What is the File Droid GUID for `NoNeedToWonder?

This can be found using Zimmerman's JLECMD tool. It is found at entry #70.

A: ec2ab952-7e4d-11f1-89ad-a2dead7852ad


What hostname associated with this entry?

Same as previous question

A: logging-vm


What was the original name of the folder?

This can be found with strings or a hexdump of the entry.

A: SoulSearching

Flag: `L3AK{P4r4n0rm4l_P4r4ll3l_P47h5}`
