.global _start

#define STRLEN 0

_start:
    .intel_syntax noprefix
    push rbp
    mov rbp, rsp

    mov rax, [rdi+STRLEN*8]
    push rsi
    mov rdi, rsi
    call rax
    pop rcx
    mov rsi, rcx
    add rcx, rax
    sub rcx, 1
    mov BYTE PTR [rcx], 0


    mov rdi, rsi
    mov rsi, 0
    mov rdx, 0
    mov rax, 2
    syscall

    cmp rax, 0
    jle error

    mov rsi, rax
    mov rdi, 1
    mov rax, 40
    mov rdx, 0
    mov r10, 0xFFFFFFFF
    syscall
    leave
    ret

error:
    lea rsi, [rip+error_str]
    mov rdx, 24
    mov rdi, 1
    mov rax, 1
    syscall
    leave
    ret

error_str:
    .string "Something went wrong :(\n"
