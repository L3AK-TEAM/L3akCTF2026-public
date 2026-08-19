/* prism.ld -- linker script for PRX job binaries. */
OUTPUT_ARCH(mips)
ENTRY(_start)

PAGE_SIZE = 0x1000;
LOAD_BASE = 0x00400000;

/* FLAGS describe the intermediate ELF only */
PHDRS
{
  text PT_LOAD FLAGS(0x5);   /* R+X: .text */
  data PT_LOAD FLAGS(0x6);   /* R+W: .rodata .data .sdata .bss */
}

SECTIONS
{
  . = LOAD_BASE;

  .text : {
    *(.text .text.* .gnu.linkonce.t.*)  /* e_entry comes from the ELF; _start placement is irrelevant */
  } :text

  . = ALIGN(PAGE_SIZE);

  .rodata : {
    *(.rodata .rodata.* .gnu.linkonce.r.*)
  } :data

  .data : {
    *(.data .data.* .gnu.linkonce.d.*)
    *(.sdata .sdata.*)                  /* vestigial under -G0; kept for small-data mode */
  } :data

  .bss (NOLOAD) : {
    *(.sbss .sbss.* .scommon)
    *(.bss  .bss.*  COMMON)
    . = ALIGN(4);
  } :data

  /DISCARD/ : {
    *(.reginfo) *(.MIPS.abiflags) *(.gnu.attributes)
    *(.note .note.* .comment .pdr .mdebug .mdebug.* .eh_frame .eh_frame_hdr)
  }
}
