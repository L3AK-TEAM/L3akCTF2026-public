.global _start

#define STRLEN 0


_start:
    .intel_syntax noprefix
    push rbp
    mov rbp, rsp
    # rdi: function table
    # rsi: argv

    mov rax, [rdi+STRLEN*8]
    mov rdi, rsi
    push rsi
    call rax    

    mov rdi, 1
    mov rdx, rax
    pop rsi
    mov BYTE PTR [rsi + rdx], 0x0a
    inc rdx
    mov rax, 1
    syscall

    

    leave
    ret
    

