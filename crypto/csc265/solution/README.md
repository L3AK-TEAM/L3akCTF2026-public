# CSC265 Solution
### Author: Toadytop

The challenge closely follows https://eprint.iacr.org/2013/515.pdf. The main diferences are that the elements are hashed, which prevents one who knows partial information about
the elements from doing some simple linear algebra to enumerate all the elements. The other is that there is both an encrypted version and decrypted version of the GBF, which only differ in 32 
entries. 

This means, that when we truthfully follow the protocol, using our on bloom filter with 1/4 of the entries empty, we learn almost the entire garbled bloom filter, up to about 8 entries that are unknown.
Thus at the end when we get the nonce, we can try looking up every possible element of the form `(nonce, i, s)`, where `i` ranges from 0 to 31, and `s` is in the 32-character alphabet. So this requires 1024
attempts to find easy elements. If we by reasonable chance get 25 such confirmed spots, the remaining elements can be brute forced against the hash, and we can also do some early rejection of candidates.
Those candidates that we reject are the ones where if, for example, element 1 is known, and it has empty slot in index 23 (which can be identified by diffing the encrypted and the decrypted GBF, note that
we sometimes can't identify this, specifically when multiple of the entries corresponding to an element are different, so unless we know one of them to be an empty slot for a previous element, we can't
know exactly which was the empty slot), then element 0 cannot have any corresponding index of 23, as then 23 would not have been the first empty slot for the next element. 

Thus all that remains is to keep trying the remote until we get a little bit lucky (25 is not far from 24), and we can then find the secret. 

Flag: `L3AK{why_d1d_th15_B3come_4_ppC_ch4ll3nge???}`
