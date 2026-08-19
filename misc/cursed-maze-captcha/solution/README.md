# Cursed Maze Captcha Solution
### Authors: Suvoni, JAGIC

Start a session with `/api/start` and keep the session cookie, then use the returned `hWalls`, `vWalls`, `entrance`, and `exit` values to rebuild the 11×11 maze. A simple breadth-first search gives the unique shortest route, and each position on that route can be sent in order to `/api/move` along with the round’s `submitToken`. Repeating this for all 100 rounds is easily fast enough to beat the 20-second timer, and the final response contains the flag.

Alternatively, you could have tried to solve it by hand, as the 20-second timer leaves enough time to solve it if you're fast. The maze rotation and color gradient don't make it easy though...

Flag: `L3AK{I_H0pe_Y0u_D1dnT_5oLV3_i7_by_h4nD_B3C4u5E_tHAt_W0uLd_B3_trUlY_CuR53D}`
