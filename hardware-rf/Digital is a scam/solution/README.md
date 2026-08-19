# Digital is a Scam Solution
### Author: Suvoni

The circuit is quite massive and seems daunting at first glance: the flag is sent as binary through a capacitor DAC and then propagates through a large irregular resistor network, op-amp network, and several current mirrors to the final analog output node. If you research the math behind analog circuit elements, you can figure out that each stage is actually linear, which means we can simplify it down to a single constant multiplier. We tackle the resistor network using Kirchhoff’s laws to figure out the voltage at net_tap. Each op-amp and current mirror will either provide a gain or flip the sign. When we multiply all those values together, we get the total gain of the circuit. This means that the output we measure is actually the unknown DAC value multiplied by that gain. To get back to the original integer encoded by the flag bits, we just divide by the gain and then multiply by \(2^N\).

If you like this type of challenge, you may be an electrical engineer at heart :) 

Some advanced resources for further study:
- *CMOS Analog Circuit Design* by Phillip E. Allen
- [Behzad Razavi's Analog Electronics Youtube videos](https://youtube.com/playlist?list=PLYn9CiLoELn-y082qk-GcLvMBF4SzG6hy)

Flag: `L3AK{Cl0wN1nG_4r0uNd_w1th_4n4LoG_ciRcu1t5}`
