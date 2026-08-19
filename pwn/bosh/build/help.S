.global _start

#define STRLEN 0
#define PRINTF 1
#define MODULES 2

_start:
    .intel_syntax noprefix
    push rbp
    mov rbp, rsp
    sub rsp, 8
    mov [rbp-8], rdi
    # rdi: function table
    # rsi: argv

    mov rax, [rdi+MODULES*8]
    mov rax, [rax]
    push rax
loop:
    mov rsi, [rsp]
    mov rdi, [rbp-8]
    call print_one_module
    mov rsi, [rsp]
    cmp QWORD PTR [rsi+0x18], 0
    je end
    pop rcx
    mov rsi, [rsi+0x18]
    push rsi
    jmp loop
end:
    pop rax
    leave
    ret
    

print_one_module:
     push rbp
     mov rbp, rsp
     sub rsp, 0x10
     mov [rbp-8], rsi
     mov [rbp-0x10], rdi
     # rdi: function call table
     # rsi: module struct

     mov rax, [rdi+STRLEN*8]
     mov rsi, [rsi];
     push rsi
     mov rdi, rsi
     call rax
     # Put name length into rax

     mov rdx, rax
     mov rax, 1
     pop rsi
     mov rdi, 1
     syscall

     mov rax, 1
     mov rdi, 1
     lea rsi, [rip+separator]
     mov rdx, 3
     syscall

    mov rax, [rbp-0x10]
    mov rax, [rax+STRLEN*8]
    mov rsi, [rbp-8]
    mov rsi, [rsi+8]
    push rsi
    mov rdi, rsi
    call rax

    mov rdx, rax
    mov rax, 1
    mov rdi, 1
    pop rsi
    syscall


    mov rax, 1
    mov rdi, 1
    lea rsi, [rip+nl]
    mov rdx, 1
    syscall
    
    leave
    ret

    

    #Print name

separator: 
    .string " - "
nl:
    .string "\n"
 
