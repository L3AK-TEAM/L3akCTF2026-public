#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <string.h>
#include <stdint.h>
#include <sys/stat.h>
#define MAX_MODULES 255

#define ARRAY_LENGTH(arr) (sizeof(arr) / sizeof((arr)[0]))

typedef struct {
	uint32_t nameLen;
	uint32_t helpLen;
	uint32_t codeLen;
} mheader_t;

typedef struct module_t {
	char *name;
	char *help;
	void (*code)(uint64_t *, char *);
	struct module_t *fwd;
	struct module_t *bck;	
	long codeChecksum;
} module_t;

const char *const modules[] = {
	"modules/echo.mod",
	"modules/help.mod",
	"modules/cat.mod",
	"modules/exit.mod",
	"modules/ray.mod"
};

char previousCommand[512];
module_t *modules_head;

const uint64_t pointers[] = {
	(uint64_t)&strlen,
	(uint64_t)&printf,
	(uint64_t)&modules_head,
	(uint64_t)&atoi,
	(uint64_t)&memset
};

int moduleCounter = 0;

void dbg_print_module(module_t *m){
	printf("Module %s:\n", m->name);
	printf("\tHelp text: %s\n", m->help);
	printf("\tCode mapping: %p\n", m->code);
	return;
}

void dbg_print_list(){
    module_t *m = modules_head;
    while(m != NULL){
        printf("[%s] -> ", m->name);
        m = m->fwd;
    }
	puts("");
}


void crash(char *msg){
	printf("Fatal error: `%s`\n", msg);
	exit(0);
}

void populate_module_buffers(module_t *m, mheader_t *h){
	m->name = malloc(h->nameLen);
	m->help = malloc(h->helpLen);
	
	int numPages = (h->codeLen >> 12) + 1;

	m->code = mmap((void *)(0x1337000 + (moduleCounter*0x1000)), numPages * 0x1000, PROT_READ | PROT_WRITE | PROT_EXEC, MAP_PRIVATE | MAP_ANONYMOUS, 0, 0);
	moduleCounter++;
	if(m->code == 0 | m->name == 0 | m->help == 0){
		crash("Failed to initialize module");
	}

	return;
}

module_t *load_module(char *path){
	mheader_t header;
	module_t *mod;
	int fd;
	int nameReadSz, helpReadSz, codeReadSz;
	
	mod = malloc(sizeof(module_t));
	fd = open(path, O_RDONLY);
		
	if(read(fd, &header, sizeof(mheader_t)) < 0){
		crash("Failed to open module");
	}
	
	populate_module_buffers(mod, &header);
	

	nameReadSz = read(fd, mod->name, header.nameLen);
	helpReadSz = read(fd, mod->help, header.helpLen);
	codeReadSz = read(fd, mod->code, header.codeLen);
	mprotect(mod->code, header.codeLen, PROT_READ | PROT_WRITE | PROT_EXEC);
	if(nameReadSz < 0 | helpReadSz < 0 | codeReadSz < 0){
		crash("Failed to read module");
	}
    return mod;
};

int install_module(char *path){
	module_t *mod;

	mod = load_module(path);
	mod->fwd = modules_head;
	if(modules_head != 0){
		modules_head->bck = mod;
	}
	modules_head = mod;
	return 0;
}

void interpret_cmd(char *full_cmd){
    char *cmd = malloc(strlen(full_cmd) + 4);
    memcpy(cmd, full_cmd, strlen(full_cmd));
    char *p = strchr(cmd, ' ');
    if(p == NULL){
	p = cmd + strlen(cmd) - 1;
    }
    *p = '\0';
    char *args = p + 1;
    module_t *m = modules_head;
    while(1){
		if(strcmp(m->name, cmd) == 0){
			m->code(pointers, args);
			break;
		}
		else if(m->fwd != NULL){
			m = m->fwd;
		}
		else{
			printf("No module called %s loaded.\n");
			break;
		}
    
    }
}

void doShell(){
	char *cmdBuf = malloc(0x512);
	while(1){
		printf("boosh>");
		int cmdLen = read(0, cmdBuf, 0x512);
		if(cmdLen <= 0){
			free(cmdBuf);
			return;
		}
		if(strcmp(cmdBuf, "prev") == 0){
			interpret_cmd(previousCommand);
		}
		else{
			memcpy(previousCommand, cmdBuf, cmdLen);
			interpret_cmd(cmdBuf);
			memset(cmdBuf, 0, cmdLen);
		}
		
	}
}

void protect(){
	int e = 0;
	for(int i = 0; i < ARRAY_LENGTH(modules); i++){
		e += chmod(modules[i], 0);
	}
	e += chmod("flag.txt", 0);
	if(e != 0){
		puts("ERROR: Failed to protect modules/flag");
		exit(0);
	}
}

void unprotect(){
	for(int i = 0; i < ARRAY_LENGTH(modules); i++){
		chmod(modules[i], S_IRUSR | S_IWUSR);
	}
	chmod("flag.txt", S_IRUSR | S_IWUSR);
}

void load_modules(){
	puts("Loading modules...");
	for(int i = 0; i < ARRAY_LENGTH(modules); i++){
		printf("\tLoading module %s...\n", modules[i]);
		install_module(modules[i]);
	}

}

int main(){
    setvbuf(stdin, NULL, _IONBF, 0);
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stderr, NULL, _IONBF, 0);

	unprotect();
    load_modules();
    protect();

    doShell();
}
