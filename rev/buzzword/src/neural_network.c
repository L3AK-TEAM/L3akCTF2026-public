#include <unistd.h>
#include <sys/ptrace.h>
#include <immintrin.h>
#include <string.h>
#include <stdint.h>
#include <stdio.h>

// Applogies for the poor code style, this essentially does multiple matrix multiplications
// then it checks the length of the final output vector and it must be under a threshold
// it's essentially just MLWE, so BKZ (not just LLL) will work. Some obfuscation used:
// anti-analysis inlined assembly. I used baresifter on my CPU to find valid instructions
// that disassemblers can't disassemble, some are inlined here. There's also large nop
// blocks which I noticed makes analysis more annoying in Ghidra specifically. 
// The gf_inv stuff and diffuse stuff is just to make in non-trivial to understand the structure.
// The fork/ptrace stuff is basic anti-debug. 

// flag: L3AK{it's_a_svp_challenge?_everything_is.} len=42
#define b_inc b = 251 * ~(b & b) + 135 * ~b + 234 * (~b ^ ~~(b | b)) + 229 * b + 183 * (~(b & ~b) ^ (~(b ^ b) | ~(b & b)) ^ ~(~(b & b)& ((b | b) ^ ~b))) + 36 * (~(b ^ b ^ b ^ b ^ ~b) | b) + 249* (((b | b) & (b | b) ^ ~b | ~(b ^ b) | ~(b | b)) ^ (~b | b^ b | ~b | ~b) & b) + 154 * ~(b | (b & b | b ^ b) ^ (b ^ b |b)) + 74 * ((b ^ ~b | b & b) & ~~(b ^ b) ^ b) + 19 * (b &~(b ^ b & b | b & (b ^ b))) + 68 * (((b ^ b | ~b) ^ b ^ (b |b)) & b ^ ((b | b) ^ b ^ b) & ~~b ^ b) + 203 * ((b ^ b) & ~((b | b) & b & b) & (b ^ b ^ b ^ b ^ b ^ b))
#define i_inc i = 7466205376912898259 + 17203492052378142966 * (~(~i & ~i)^ i) + 11620061416039919923 * (~((i & (i & i ^ i & i) | i |i & i | i ^ i ^ i ^ i | ~~(i & i) | i ^ (i ^ i) & (i | i)) ^~~(i | i)) ^ ~i) + 10015517450184168906 * ~(i & ((i ^ i & i^ i ^ i | (i ^ (i | i)) & ~(i ^ i)) ^ (i ^ i) & (i ^ i) & (i& i ^ (i | i)) ^ ~(i & i & (i | i))) ^ (i ^ (i & i | i) & i& i & i & ~((i | i) ^ i & i)) & i) + 7967367868848697173 *(i | i) + 10431524518914635450 * (~(~(~(i | i) ^ i ^ i ^ i)^ (i | ~(i | i) ^ (i | i | i)) ^ ~(((i | i) & ~i | i) & i))| i ^ i & ((i | i | i | i) ^ i ^ (i | i) & i & (i ^ i ^ (i |i)) ^ (i & i ^ ~i | (i | i) & i & i) ^ (i ^ i) & ~i & i & (i| i))) + 5437867893461985926 * i + 14996341359536160282 *~(i & i | (i | i | i) & i | i | i | (i & i ^ (~(i | i) & (~i^ i) | ~(~i | ~i))) & (i ^ i ^ ~((i | i) ^ i ^ i))) +14800611739636574138 * ~i + 16679010470539184235 * ~(i ^~(~i ^ i ^ i | (i | i) ^ i & i) & (~~i ^ (i | i) ^ i & i) &i | ~(i ^ i) & (i | (i | i | i) & (i ^ i & i)) | (i ^ i | i& (i | ~i)) & ~(i | i ^ i ^ ~i)) + 14093670748394910589 *(~((i | ~(i ^ i ^ ~i)) & i & ((~i | ~i | i | ~(~i ^ i)) ^i)) | ~i) + 4024104664825056178 * (~(i & (i | ~(i ^ i)) | i| i) | (~((i | i | i | i) ^ (i ^ i) & i & i) | i | i ^ i & i& ~i) & (i & i & (i | i) | i) & (~~(i | i) ^ i) & i) +4004475601889836668 * (((i & ~i | i ^ i & i) ^ i) & (~(i | i| i ^ i) ^ ~(i & (i | i))) | i & (i ^ ~(i ^ i) ^ (i | i |i)) | i ^ ~(i | i) ^ (i | i | i | i ^ i) ^ ~i | (i & ~(i & i& (i | i) & i) | ~((i | i | i ^ i) & ((i | i) ^ ~i) | (i ^ i^ i) & ~i & (i ^ i))) ^ (~(~i & ~(i | i) | (i ^ i) & (i ^ i)| ~i) | i)) + 7548356905956306684 * (~(i & (~(i ^ i) | i)) ^~(i & ~i & i) & (~(i ^ i | i ^ i) ^ i & i) & (i ^ i ^ (i |~i ^ i) | i) ^ ~i ^ (i ^ ~~~i ^ i & (i & i | ~i | i | i)) &~i) + 14977067273151929115 * ~(~(~~(i & i ^ i) & i) ^ ~(((i| i) ^ i & i | ~i | i | i) & ~~i) ^ (i | ~(~i ^ i) ^ (i ^ i| i) ^ i & (i ^ i))) + 1550068062474373672 * ((~(~i & (i & i| ~i | i ^ (i | i))) ^ i) & ((~i ^ i ^ i & i ^ ~i) & i | i |i & i & i) & (i | (~i & (i | i) | ~(i ^ i)) & i & i & ~i &(i ^ (i | i)) | ~(~((i ^ i) & i & i) ^ i)) & (~~i | ~i | ~i)& ((i | i) & i & i ^ i & i & i) & (i | ~(~i & i & i)) & ~~(i& i & i & i) & (~(i ^ i) ^ (~i | i)) & ((i & i | i & i) ^ i& i & (i | i))) + 2399930646098585651 * ~(i | (i ^ ~i ^ i ^i) & ~(~i ^ i ^ i) & ((i | i) ^ i ^ i ^ i ^ i & i) & i ^ i)+ 14025840661851962820 * ~(~((~i & i | i ^ (i | i)) ^ ~(i &i) & ~i ^ i) | ~((i ^ ((i | i) ^ ~i) & (i ^ i | i | i)) &((i | i & i) ^ (i | i | i | i) ^ (i | i ^ i | ~i)))) +14854596253845842960 * (~i ^ i & (i | ~((i ^ i) & (i ^ i)))& ((i ^ ~i | ~i ^ i) ^ i ^ i & i ^ (i | i)) ^ (i & i ^ i) &(i & i ^ i)) + 12841712414929408628 * ~(i & ((i | i) & ~i ^i ^ (i ^ (i | i) | ~(i & i)) ^ (~i | i & i ^ i ^ i | (i | i)^ i & i)) & i) + 801582281860639830 * (~((i ^ i | i ^ i | ~i| i ^ i) & (i | i) & i & i) ^ ~((~i | ~i) & ~~i) & i ^ i | i^ (i & i | i | i ^ i | i & i) ^ ~~i & (i ^ i ^ ~i) & ~(i & i& i) ^ ~(i ^ i) & (i ^ i | i | (i | i) & (i ^ i)) ^ i ^ (i &i | i) & (i ^ (i | i)) ^ (i | i) ^ ~~(i & (i | i | i ^ i)))+ 8052254388432816924 * ((i & (i & (i ^ i) ^ ~i ^ i) ^ ~(~i| (i | i) & i & i) | ~i & (i | i) ^ i & i & ~i ^ (i ^ i ^ (i| i)) & ~(i ^ i) | ~(i ^ i) & ~~i & (~i | ~i) | i) & i) +8724699586371002281 * (i ^ i) + 9754330832005452553 *(~(~((i ^ i ^ ~i) & (i | i) & i & i | ~(i ^ i | i | i)) & i)| i) + 15730876962761246857 * ~((~~(i ^ i & i & (i | i)) ^((i | i) ^ i ^ i | ~~i | i & i ^ (i | i) | i & i | ~i | i &i & (i ^ i) | ~i | i | i | ~((i ^ i) & (i | i)))) & ~(i &~((i | i) & (i ^ i)) | i)) + 16844636420916625666 * (i & i &~(i | ~(i & i & i & ~(i | i)) ^ (~(i | i) ^ (i & i | i | i)| i))) + 5650885646791184990 * (((~(~i & ~i) | i | ~(~(i |i) | i & (i ^ i))) ^ ~~((i & i & i & i ^ ~~i) & ((i | i) ^(i | i | i ^ i)))) & ~((i ^ i & ~(i & i)) & i | i ^ (i | i)^ (~i | i ^ i | ~i & i))) + 15543178624961748010 * (((i ^~(i & i) ^ i ^ i | i) ^ i | ~~(~i ^ (i | i)) & (i | i) & (i| ~i) & ~i ^ ~(i & i) & (~i ^ i ^ i) ^ (~(i | i) | i | i |i) ^ i & i ^ i ^ i ^ i ^ ~i ^ i) & i) + 3639818081630202165* (((i ^ (i | i)) & (i ^ (i & i | i ^ i) ^ i ^ i ^ (i | i))| i & (i ^ i) & ~i | (i | i) ^ i ^ (i | i | i) | i | (i | i)& ~(i | i)) & i & i & i) + 4433458206293371265 * (~i & i & i& i & ~~(~(i | i) & ~(i | i) ^ ~~(i & i)) ^ (i ^ ~i & i ^~i) & (i ^ i ^ i & i) & (i | i) & i & i ^ ~(i | i | i ^ i) &(i | i) & (i | i) & i ^ i ^ i ^ i) + 5920947572391554797 *(i & ~(~(i & (i & i ^ ~i)) & ((i & i | i) & ~i & i | ~(i |i) & (i & i ^ i ^ i)) | i)) + 17270478118111806546 *((~((~(i & i | ~i) ^ i) & (~i ^ (i | i)) & ~(i | i) & ~(~i &(i | i))) | ~(~i ^ i)) ^ ~((~((i ^ i) & (i | i)) | (i ^ i) &i & i ^ i | ~i) ^ ~(i & i ^ i ^ i | ~i | i & i) & (i ^ i & i& i ^ ((i ^ i) & (i ^ i) | i & i | i & i)))) +15653468853858443042 * (i & i | i) + 13019415084079631585 *(((i ^ i & ((i | i) ^ (i | i)) ^ ~i) & (~~i | ~(i ^ i)) &~((i | i) & i) & (i | i) | ~i & ~~i | ~((i & i ^ i) & ~(i &i) | i | i & i | ~i)) ^ ~~((~(i | i) | i) ^ (i & i | ~i) ^~i ^ ~(i & i ^ (i | i)))) + 9916132700458148816 * (~(i &~((~(i & i) ^ i) & (i ^ i ^ i ^ i ^ i))) ^ i) +8926035401783461686 * ((i ^ ~(~i | i & i) ^ ~i ^ i ^ (i ^ i| i & i) & i | ~(i ^ (i | ~(i ^ i)) ^ i)) ^ (i | ~i)) +7887788615180408921 * ((i & (i ^ i) | (i | i) ^ ~i) ^ i | (i^ (i | i) & (i ^ i)) & (~(i ^ i) ^ i) | i | (i | ~i & i & i)& (i & i | i | i) & i & (i | i) | ((i ^ i & i) & ~((i ^ i) &i) ^ (~i | i | i) & ~i & i & i & i) & (i | ~(i | i | i) & (i^ i)) | (~~i & (i | i | i | i) & (~i ^ i ^ i ^ ~(i ^ i)) &~(i | i | i) & ~(i | i ^ i) | (i & ~i | i ^ i ^ i | i ^ (i |i | ~i)) & ~i) ^ ~i) + 8734367710272273618 * (~(i & (~i & i& (i ^ i | i ^ i) & i & i & (i | i) ^ ~~(i & i) & ~i)) | i)+ 15309713293165073359 * ((i ^ ~((i ^ i) & (i | i) ^ (~i | i& i)) & (~(i ^ i ^ i & i) | i) ^ ~i) & ((~(i | i | i ^ i) &(~i ^ i ^ i ^ ~i & ~i) | ~i & i & i ^ i | i) & i ^ (i ^ (~i| ~i) | ~(i | i) | i | ~(i | i)) & ~((~i ^ i ^ i) & (i ^ i ^i & i)) & (~(~i | i | i) ^ (i | i ^ i & i))))
__attribute__((always_inline)) inline uint64_t gf_inv(uint64_t input);
#define expand_me_to_gf_inv gf_inv(e)

/*uint64_t f(uint64_t a, uint64_t c, uint64_t d, uint64_t e) {
    return (a+(expand_me_to_gf_inv*c)+(e*d));
}*/
__attribute__((always_inline)) inline uint64_t f(uint64_t a, uint64_t c, uint64_t d, uint64_t e) {
	uint64_t v2 = (8280399212160308982 + 1686941012908093870 * ~~(~e
		& (expand_me_to_gf_inv & (d ^ d | ~expand_me_to_gf_inv) &
		~(a & a) | e)) + 12415447591687339830 * ~d +
		7415584164249226878 * ~~(c & ~(e ^ expand_me_to_gf_inv | c |
		c) & expand_me_to_gf_inv ^ d) + 864815047911082104 * (~e |
		e) + 13446880646271438664 * ~(~(d & a) ^ ~(d &
		~(~expand_me_to_gf_inv & a & e)) | d) + 12785292546263132535
		* ~(d | ~((d ^ ~c) & a & d & ~c) | (~c ^ ~e) & ((c | d) ^ (e
		| expand_me_to_gf_inv)) & (expand_me_to_gf_inv & e ^ e | d ^
		e ^ c) | ~(d | (~c | e ^ a) & (~c | e)) & (c &
		expand_me_to_gf_inv | d) & ~(d ^ (e | c) ^
		~(expand_me_to_gf_inv | expand_me_to_gf_inv))) + 1 *
		expand_me_to_gf_inv) * (11063680510727534167 +
		17875440518913074417 * ((e | d | ~(a & c & a) | (a ^ c |
		expand_me_to_gf_inv) ^ ~(e & a)) & d & expand_me_to_gf_inv |
		~~(e & expand_me_to_gf_inv ^ a & e | d) | d | c ^ (d ^ d |
		expand_me_to_gf_inv) | expand_me_to_gf_inv ^ e & ~a ^ c |
		~(d & e & (~expand_me_to_gf_inv | expand_me_to_gf_inv & (c |
		d) & a))) + 1 * c + 2411612028669235558 * d +
		9223372036854775808 * expand_me_to_gf_inv +
		11634984065524011366 * ~d + 9223372036854775808 *
		(expand_me_to_gf_inv ^ ~((~~d | expand_me_to_gf_inv) & (a ^
		(d | e) ^ e) & ~(~a | ~c | (expand_me_to_gf_inv | a) ^ d ^
		d)) ^ (~(~c | a & d) & expand_me_to_gf_inv & e & d | e) & c)
		+ 9223372036854775808 * (((((e | a) ^ d ^ a) &
		expand_me_to_gf_inv & (c ^ d) | expand_me_to_gf_inv ^
		(expand_me_to_gf_inv | c) ^ expand_me_to_gf_inv ^ c |
		~(~~expand_me_to_gf_inv ^ e)) ^ ~~~expand_me_to_gf_inv) & c
		^ ~d));

	uint64_t v1 = (10522642432715295522 + 679001745385763482 * ~a +
		679001745385763482 * a + 18400729655013981176 * ~((~e | ~(e
		| d & expand_me_to_gf_inv ^ ~a) | d & e & a & (a | d) & (a ^
		d) & ((~c | e & d) ^ c & (d ^ a)) & (a ^ ~(a & d)) & ((c ^ c
		| d) ^ expand_me_to_gf_inv ^ a ^ ~d)) ^ (expand_me_to_gf_inv
		| d | d ^ a | (expand_me_to_gf_inv | a) ^
		~expand_me_to_gf_inv | ~(a | d | c | d) |
		~(~expand_me_to_gf_inv & (d ^ d) ^ e ^ d ^ (d | c)))) +
		9889655106025102480 * (~c | c) + 18400729655013981177 * e) *
		(8094887138492733629 + 12792135065872336314 *
		expand_me_to_gf_inv + 9300015521138194700 * e +
		2978571840435305139 * ~~expand_me_to_gf_inv +
		10654532883056293418 * ((~(~a & ((expand_me_to_gf_inv | d |
		e | d ^ c) ^ e)) ^ (~~(a ^ a) | ~~(~(expand_me_to_gf_inv |
		a) | e & e ^ e ^ a))) & ~((c ^ expand_me_to_gf_inv |
		expand_me_to_gf_inv & c ^ d & e | c ^ e ^ a | ~(c & d)) ^ (a
		& d & c | d ^ e | d ^ c) & (e | a) & a & c & (e ^ c)) &
		(~(~e & ~expand_me_to_gf_inv ^ d ^ a ^ ~a | (e & e | e | c)
		& (~expand_me_to_gf_inv | e)) | (e | d) ^ (~e ^ (e | c) | (a
		| c) ^ a | ~expand_me_to_gf_inv))) + 15582331412401569571 *
		(c | c & (d | (e & e | expand_me_to_gf_inv & a) ^ (d | e) ^
		~expand_me_to_gf_inv | c | (c | expand_me_to_gf_inv) & (d |
		a) & (c & d ^ ~a)) & (d ^ c)) + 1 * d + 9043491216531234164
		* (d | ~d & ((e ^ d | d | d) & expand_me_to_gf_inv & (c |
		expand_me_to_gf_inv) ^ ~(expand_me_to_gf_inv ^ c | e | a)) |
		(~((e ^ e ^ c & d) & expand_me_to_gf_inv) |
		~(expand_me_to_gf_inv | expand_me_to_gf_inv) ^ ~(c &
		expand_me_to_gf_inv) ^ (d & d | d) & ~expand_me_to_gf_inv) ^
		expand_me_to_gf_inv | (expand_me_to_gf_inv &
		~(expand_me_to_gf_inv ^ a | a ^ e) ^ (e | d) & a & a & c &
		expand_me_to_gf_inv & expand_me_to_gf_inv) & e ^ ~(~((a |
		expand_me_to_gf_inv) & ~a | ~a | a) & d)) +
		15770706906307641453 * ~expand_me_to_gf_inv +
		6324056081754170493 * (e & (~((d | a | c & d) & ~~d & ~(e &
		c & c)) | c ^ ~a ^ a) ^ (~(~a | expand_me_to_gf_inv | c & a
		& (d | c)) | expand_me_to_gf_inv | ~expand_me_to_gf_inv)) +
		15582331412401569571 * ~c + 15470784634325527409 *
		((~(expand_me_to_gf_inv & expand_me_to_gf_inv & ~c) & (d &
		expand_me_to_gf_inv | ~a | a ^ e ^ (expand_me_to_gf_inv |
		e)) | ~~c | d & (expand_me_to_gf_inv | expand_me_to_gf_inv |
		c | expand_me_to_gf_inv ^ d | a | e) | ~(expand_me_to_gf_inv
		^ d ^ e ^ e) ^ (expand_me_to_gf_inv & expand_me_to_gf_inv ^
		(a | d) | ~(e & d)) | e | (d | expand_me_to_gf_inv | e | e &
		e & e) & ((d ^ expand_me_to_gf_inv) & ~d | e ^ c ^ d) &
		(~~expand_me_to_gf_inv ^ (e ^ expand_me_to_gf_inv) &
		expand_me_to_gf_inv & a) & (expand_me_to_gf_inv ^
		expand_me_to_gf_inv) & c & expand_me_to_gf_inv & a) ^ ~e) +
		16714533742626772796 * (~(((d & c | ~e | c & c) ^
		(expand_me_to_gf_inv | ~e)) & (c | ~d)) ^ ~((c ^ d | e ^ c)
		& (a ^ a | e & expand_me_to_gf_inv) & ~~(c ^ a) ^ (d ^ ~e |
		~e)) | ~(d | ~((expand_me_to_gf_inv | expand_me_to_gf_inv) &
		(e ^ expand_me_to_gf_inv))) ^ (expand_me_to_gf_inv & e |
		expand_me_to_gf_inv | ~(expand_me_to_gf_inv ^ c) | ~a | c &
		a | ~e ^ a) ^ d & (e & expand_me_to_gf_inv |
		expand_me_to_gf_inv) & ((expand_me_to_gf_inv ^ a) & ~e ^ (~d
		| c)) ^ (c ^ ~e ^ d ^ e & d ^ e) & ((expand_me_to_gf_inv ^ a
		| a & e) ^ a) & ~~~e & ~(e & expand_me_to_gf_inv | (d ^ a) &
		~c)));

	return 6002522663683723544 * (a | ((e | ~(v1 &
		expand_me_to_gf_inv | e ^ d) | expand_me_to_gf_inv & (v1 ^ c
		^ v2 ^ e) ^ (expand_me_to_gf_inv ^ v2 | e ^ e) & (d | d | e
		& c)) ^ expand_me_to_gf_inv) & expand_me_to_gf_inv & a) +
		12444221410025828073 * a + 9223372036854775808 * d +
		12433915238524388710 * ~(d | ~(a & expand_me_to_gf_inv & v1
		& expand_me_to_gf_inv & ~(a & a & ~v1)) |
		expand_me_to_gf_inv) + 9223372036854775808 * (v1 ^ (e | e))
		+ 1 * ((v2 | ~(c | v1 | ~e | (a | d) & (e | a)) | ~(e ^ c ^
		~e) ^ d ^ (v2 ^ a ^ (expand_me_to_gf_inv | a)) & v2 & a & v2
		^ ~(e ^ e) & ~(v2 | a)) & v2) + 9223372036854775808 * (d ^
		e) + 9223372036854775809 * v1;
}



__attribute__((always_inline)) inline uint32_t deinterleave_bits(uint32_t x) {
    return _pext_u32(x, 0x55555555) | _pext_u32(x, 0xAAAAAAAA) << 16;
}
__attribute__((always_inline)) inline __m128i gf_inv_real(__m128i x) {
    uint64_t I = 0x0102040810204080ULL;;
    __m128i A = _mm_set_epi64x((int64_t)I, (int64_t)I);
    return _mm_gf2p8affineinv_epi64_epi8(x, A, 0);
}
__attribute__((always_inline)) inline uint64_t gf_inv(uint64_t x) {

    uint8_t bytes[16] = {0};
    memcpy(bytes, &x, 4);
    __m128i y = _mm_set_epi8(
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,bytes[3],bytes[2],bytes[1],bytes[0]);
    __m128i z = gf_inv_real(y);
    _mm_storeu_si128((__m128i *)bytes, z);
    uint32_t a = 0;
    memcpy(&a, bytes, 4);
    uint64_t ret = 0;
    ret = (uint64_t)deinterleave_bits(a);
    return ret;

}


__attribute__((always_inline)) inline void matrix_multiply(uint32_t layers [3][42][42], uint32_t vector [42], uint64_t layer, uint64_t modulus) {
    uint64_t temp[42] = {0};
    __asm__(".byte 0x0f, 0x0d, 0xc0\n");
    #pragma unroll
    for (int a = 0; a < 42; a++) {
        #pragma unroll
        for (uint8_t b = 0; b < 42; b++) { // b_inc) {
            __asm__(".byte 0x0f, 0x0d, 0xc0\n");
            temp[a] = f(temp[a], vector[b], 0, layers[layer][a][b]) % modulus;
        }
    }
    #pragma unroll
    for (uint64_t i = 0; i < 42; i_inc)
        vector[i] = temp[i];

}
int main () {
    // So, what's happening? 
    // First, we take an input, the flag ofc
    // Then we multiply it by a matrix over a modulu
    // Then again
    // This is trivial to reverse via gaussian eliminationn.
    // But the next layer... is the same thing.
    // But since it has a bigger modulus, and the input of the previous layer was over a small modulus
    // It kinda encodes to an MLWE problem, since we then subtract the target and compare the weight against a generous threshold.
    char in[64] = {0};
    __asm__(".byte 0x0f, 0x0d, 0xc0\n");
    int is_debug = ptrace(PTRACE_TRACEME,0);
    __asm__(".byte 0x0f, 0x0d, 0xc0\n");
    printf("Input: ");
    fgets(in, 50, stdin);
    uint32_t flag[64] = {0};
    for (int i = 0; i < 42; i_inc) {
        flag[i] = in[i];
        __asm__(".byte 0x0f, 0x0d, 0xc0\n"); // Why does this keep poping up? I found this a while ago (https://github.com/issues/created?issue=NationalSecurityAgency|ghidra|8790) by fuzzing my CPU with sandsifter (https://github.com/blitz/baresifter) and trying to disassemble valid instructions. Essentially it's marked as invalid by a few disassemblers despite being able to execute... at least on my CPU.
    }
    __asm__(
    ".fill 16384, 1, 0x90\n" // Large NOP slides sometimes make ghidra/binja act funky. It's also annoying. 
    );
    FILE *f = fopen("model.bin", "rb");
    __asm__(
    ".fill 16384, 1, 0x90\n"
    );
    uint32_t layers [4][42][42] = {0};
    __asm__(".byte 0x0f, 0x0d, 0xc0\n");
    if (is_debug < 0) {
        __asm__(".byte 0x0f, 0x0d, 0xc0\n");
       unsigned long long aaaa = (uint64_t)f; 
       __asm__(".byte 0x0f, 0x0d, 0xc0\n");
       aaaa*=2;
       __asm__(".byte 0x0f, 0x0d, 0xc0\n");
       f = (FILE *)aaaa;
       __asm__(".byte 0x0f, 0x0d, 0xc0\n");
    }
    __asm__(".byte 0x0f, 0x0d, 0xc0\n");
    #pragma unroll
    for (uint64_t i = 0; i < 42; i_inc) { // i_inc? not i++? Yup! Scroll up and you'll see an MBA-obfuscated i += 1
        fread(layers[0][i], sizeof(uint32_t), 42, f); // matrix
    }
    char haha_2[] = "Oh just try angr, it'll work for sure";
    __asm__(".byte 0x0f, 0x0d, 0xc0\n");
    #pragma unroll
    for (uint64_t i = 0; i < 42; i_inc) {
        fread(layers[1][i], sizeof(uint32_t), 42, f); // matrix
            __asm__(
        ".fill 16384, 1, 0x90\n"
        );
    }
    __asm__(".byte 0x0f, 0x0d, 0xc0\n");
    #pragma unroll
    for (uint64_t i = 0; i < 42; i_inc) {
        fread(layers[2][i], sizeof(uint32_t), 42, f); // matrix 
    }
    fread(layers[3][0], sizeof(uint32_t), 42, f); // Target vector
    int useless = fork();
    fclose(f);
    __asm__(".byte 0x0f, 0x0d, 0xc0\n");
    __asm__(
    ".fill 16384, 1, 0x90\n"
    );
    uint64_t modulus = 65537; // chosen because prime and also not a standard MLWE parameter
    __asm__(".byte 0x0f, 0x0d, 0xc0\n");
    matrix_multiply(layers, flag, 0, 127);
    __asm__(
    ".fill 16384, 1, 0x90\n"
    );
    int useless_2 = fork();
    int sigma = ptrace(PTRACE_TRACEME,0);
    __asm__(".byte 0x0f, 0x0d, 0xc0\n");
    matrix_multiply(layers, flag, 1, 127); // makes the secret small
    __asm__(
    ".fill 16384, 1, 0x90\n"
    );
    #pragma unroll
    for (uint64_t i = 0; i < 42; i_inc) {
        flag[i] = (flag[i] + (modulus - 64)) % modulus; // Makes the vector actually small
    }
    int super_sigma = ptrace(PTRACE_TRACEME,0);
    matrix_multiply(layers, flag, 2, modulus); 
    if (useless != 0 || useless_2 == 0) {
        exit(-1);
    }
    __asm__(".byte 0x0f, 0x0d, 0xc0\n");
    #pragma unroll
    if (sigma < 0 || super_sigma > 0) {
        exit(-1);
    }
    for (uint64_t i = 0; i < 42; i_inc) {
        __asm__(".byte 0x0f, 0x0d, 0xc0\n");
        flag[i] = flag[i] - gf_inv(layers[3][0][i]); // gf_inv? Something something inversion over finite field with diffusion of integers because we are storing 16bit(+1) vectors in 32 bits so I wanted to make the model file harder to understand/guess with. It also is applied on the matrixies.
    }
    printf("Output: %s\n", flag); // Astetics
    unsigned long long acum = 0;
    #pragma unroll
    __asm__(".byte 0x0f, 0x18, 0xc0\n");
    for (uint64_t i = 0; i < 42; i_inc) {
        acum += (int16_t)flag[i]*(int16_t)flag[i]; // The weights are +-1, while it may look like we're calculating a length it's just making it positive. 
    }
    if (acum < 128) { // The error is much smaller, 128 felt natural but also high enough that people wouldn't think that Auro-GE was usable.
        printf("Correct\n");
    }
}
