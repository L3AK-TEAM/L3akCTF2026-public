.global _start

#define STRLEN 0
#define ATOI 3
#define MEMSET 4

_start:
    .intel_syntax noprefix
    push rbp
    mov rbp, rsp
    
    sub rsp, 0x20
    mov [rbp-0x10], rdi
    mov [rbp-0x08], rsi
    push rbx
    mov al, BYTE PTR [rip+hasCalled]
    cmp al, 0
    # rbp-8:  argv 
    # rbp-10: function table
    # rbp-18: target address
    # rbp-20: value
    
    mov rdi, rsi
    call getspace
    mov BYTE PTR [rdi+rax], 0x00
    lea rax, [rdi+rax+1] #start of second arg
    push rax

    mov rdi, [rbp-0x10]
    mov rax, [rdi+ATOI*8]
    mov rdi, rsi
    call rax
    mov [rbp-0x18], rax

    mov rdi, [rbp-0x10]
    mov rax, [rdi+ATOI*8]

    pop rdi
    call rax

 
    mov rbx, [rbp-0x18]

    mov BYTE PTR [rbx], al
    
    mov rax, 1
    mov rdi, 1
    lea rsi, [rip+message]
    mov rdx, 89
    syscall
    jmp wipe


getspace:
    push rbp
    mov rbp, rsp
    xor rax, rax
    getspace_lp:
        cmp BYTE PTR [rdi+rax], 0x20
        je getspace_end
        inc rax
        jmp getspace_lp

    getspace_end:
        leave
        ret

message:
    .string "you've written your one byte! This module will now return immediately upon being called.\n"

wipe:
    mov rax, 0x133b000
    mov BYTE PTR[rax], 0xc3
    pop rbx
    leave
    ret
