# Maze Captcha
### Authors: JAGIC, Suvoni
This challenge was a simple programming challenge. The main idea was to use either A*, bfs, or dfs to solve the weighted maze. 

The first hurdle that you need to get through is convering the colored terminal output into usable data. Terminals use ansi-encoding to show colors in terminals, so if you use something like pwntools recvline(), you will get a bunch of extra wrapper to your colored terminal outputs.

You can get around this by searching for ansi-encoding syntax via the following format: `"\x1b\[([0-9;]*)([A-Za-z])"`. If you take a look at the commented `ansi_cells()` function in solve.py, you can see implementation of this, as well as how to store the color of a colored symbol. 

The next big issue is mapping out the maze. We can take some shortcuts here because we know all horizontal and vertical walls have space between them, so we can just check every other row and column for the maze walls. The commented `parse_maze()` function does this all. It also maps out all emoji weights to a 2d array `cells`. This will be useful for the next step.

The third and final step is to use a maze solving algorithm to complete the captcha. You could use a whole bunch of different maze solving algos such as bfs and dfs or A*. Since the maze is so small it doesnt really matter what you use. I decided to use weighted dijktra's algo since I am more familiar with it. The commented function `dijkstra()` implements this and solves the maze.

I should also note that to get the emoji widths, I imported wcwidth. A quick google search can lead you to any forum or tutorial ever. This was implemented in `width()` it just changes the length to be the actual length of smthn on the terminal.

I commented a bunch more stuff in the solve.py script, feel free to take a look at that. The main function includes a couple helper functions such as `solve_pow`, which are pretty self explanatory. Once you run the script, you get the following ascii art at the end of the 100 rounds:


```
 _       _____      _      _  __    __      _   _____   ____            _      
| |     |___ /     / \    | |/ /   / /   __| | |___ /  / ___|   _ __   / |     
| |       |_ \    / _ \   | ' /   | |   / _` |   |_ \  \___ \  | '_ \  | |     
| |___   ___) |  / ___ \  | . \  < <   | (_| |  ___) |  ___) | | |_) | | |     
|_____| |____/  /_/   \_\ |_|\_\  | |   \__,_| |____/  |____/  | .__/  |_|     
 _____   _____           _  _     _\_\_            ___         |_|____         
|_   _| |___ /          | || |   / | / |          / _ \   _   _  |  _ \        
  | |     |_ \          | || |_  | | | |         | | | | | | | | | |_) |       
  | |    ___) |         |__   _| | | | |         | |_| | | |_| | |  _ <        
  |_|   |____/   _____     |_|   |_| |_|  _____   \___/   \__,_| |_| \_\       
                |_____|           _____  |_____|             _____   _   ____  
         _ __     / \      __ _  |___ /          __      __ |___ /  ( ) |  _ \ 
        | '__|   / _ \    / _` |   |_ \          \ \ /\ / /   |_ \  |/  | |_) |
        | |     / ___ \  | (_| |  ___) |          \ V  V /   ___) |     |  _ < 
 _____  |_|    /_/   \_\  \__, | |____/   _____    \_/\_/   |____/      |_| \_\
|_____|            _      |___/          |_____|_   _   ____    _____          
  ___             / \    / | / |           (_) | | | | | ___|  |___  |         
 / _ \           / _ \   | | | |           | | | | | | |___ \     / /          
|  __/          / ___ \  | | | |           | | | |_| |  ___) |   / /           
 \___|  _____  /_/   \_\ |_| |_|  _____   _/ |  \___/  |____/   /_/     _____  
 ____  |_____|    _____   ____   |_____| |__/                          |_____| 
|  _ \  | || |   |___  | / ___|          / |  _ __             __ _            
| |_) | | || |_     / /  \___ \          | | | '_ \           / _` |           
|  _ <  |__   _|   / /    ___) |         | | | | | |         | (_| |           
|_| \_\    |_|    /_/    |____/   _____  |_| |_| |_|  _____   \__,_|  _____    
 __  __   _  _     _____  _____  |_____|             |_____|         |_____|   
|  \/  | | || |   |__  / |___ /  \ \                                           
| |\/| | | || |_    / /    |_ \   | |                                          
| |  | | |__   _|  / /_   ___) |   > >                                         
|_|  |_|    |_|   /____| |____/   | |                                          
                                 /_/                                           
```


Giving us the final flag: `L3AK{d3Sp1T3_411_OuR_rAg3_w3'Re_A11_jU57_R47S_1n_a_M4Z3}`
