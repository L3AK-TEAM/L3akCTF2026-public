#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <limits.h>
#include <png.h>

//gcc -o piet piet.c -lpng

typedef struct {
    uint32_t **pixels;
    int width;
    int height;
} Image;

typedef enum {
    UP, RIGHT, DOWN, LEFT
} dir;

typedef struct {
    int row;
    int col;
} Pos;

typedef struct {
    int32_t *stack;
    int stack_depth;
    dir CC;
    dir DP;
    int row;
    int col;
} ProgramState;

static void stack_push(ProgramState *state, int32_t value) {
    state->stack[state->stack_depth++] = value;
}

static int stack_pop(ProgramState *state, int32_t *out) {
    *out = state->stack[--state->stack_depth];
    return 1;
}

typedef long color;

static const int DR[] = { -1, 0, 1,  0 };
static const int DC[] = {  0, 1, 0, -1 };

#define BLACK 0x000000
#define WHITE 0xFFFFFF

color packColor(int lightness, int hue){
    return (long)lightness | ((long)hue << 32);
}
int lightness(color c){
    return c & 0xFFFFFFFF;
}
int hue(color c){
    return c >> 32;
}

color lookupColor(int c){
    switch(c){
        case 0xFFC0C0:
            return packColor(2, 0);
        case 0xFFFFC0:
            return packColor(2, 1);
        case 0xC0FFC0:
            return packColor(2, 2);
        case 0xC0FFFF:
            return packColor(2, 3);
        case 0xC0C0FF:
            return packColor(2, 4);
        case 0xFFC0FF:
            return packColor(2, 5);
        case 0xFF0000:
            return packColor(1, 0);
        case 0xFFFF00:
            return packColor(1, 1);
        case 0x00FF00:
            return packColor(1, 2);
        case 0x00FFFF:
            return packColor(1, 3);
        case 0x0000FF:
            return packColor(1, 4);
        case 0xFF00FF:
            return packColor(1, 5);
        case 0xC00000:
            return packColor(0, 0);
        case 0xC0C000:
            return packColor(0, 1);
        case 0x00C000:
            return packColor(0, 2);
        case 0x00C0C0:
            return packColor(0, 3);
        case 0x0000C0:
            return packColor(0, 4);
        case 0xC000C0:
            return packColor(0, 5);
        default:
            return -1;
    }
}


Image *load_png(void) {
    png_structp png = png_create_read_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
    if (!png)
        return NULL;

    png_infop info = png_create_info_struct(png);
    if (!info) {
        png_destroy_read_struct(&png, NULL, NULL);
        return NULL;
    }

    if (setjmp(png_jmpbuf(png))) {
        png_destroy_read_struct(&png, &info, NULL);
        return NULL;
    }

    png_init_io(png, stdin);
    png_read_info(png, info);

    int width  = png_get_image_width(png, info);
    int height = png_get_image_height(png, info);
    png_byte color_type = png_get_color_type(png, info);
    png_byte bit_depth  = png_get_bit_depth(png, info);

    if (bit_depth == 16)
        png_set_strip_16(png);
    if (color_type == PNG_COLOR_TYPE_PALETTE)
        png_set_palette_to_rgb(png);
    if (color_type == PNG_COLOR_TYPE_GRAY && bit_depth < 8)
        png_set_expand_gray_1_2_4_to_8(png);
    if (png_get_valid(png, info, PNG_INFO_tRNS))
        png_set_tRNS_to_alpha(png);
    if (color_type == PNG_COLOR_TYPE_RGBA ||
        color_type == PNG_COLOR_TYPE_GRAY_ALPHA)
        png_set_strip_alpha(png);
    if (color_type == PNG_COLOR_TYPE_GRAY ||
        color_type == PNG_COLOR_TYPE_GRAY_ALPHA)
        png_set_gray_to_rgb(png);

    png_read_update_info(png, info);

    png_bytep *row_pointers = malloc(height * sizeof(png_bytep));
    for (int y = 0; y < height; y++)
        row_pointers[y] = malloc(png_get_rowbytes(png, info));

    png_read_image(png, row_pointers);
    png_destroy_read_struct(&png, &info, NULL);

    Image *img = malloc(sizeof(Image));
    img->width  = width;
    img->height = height;
    img->pixels = malloc(height * sizeof(uint32_t *));

    for (int y = 0; y < height; y++) {
        img->pixels[y] = malloc(width * sizeof(uint32_t));
        png_bytep row = row_pointers[y];
        for (int x = 0; x < width; x++) {
            uint8_t r = row[x * 3 + 0];
            uint8_t g = row[x * 3 + 1];
            uint8_t b = row[x * 3 + 2];
            img->pixels[y][x] = ((uint32_t)r << 16) | ((uint32_t)g << 8) | b;
        }
        free(row_pointers[y]);
    }
    free(row_pointers);

    return img;
}

void free_image(Image *img) {
    for (int y = 0; y < img->height; y++)
        free(img->pixels[y]);
    free(img->pixels);
    free(img);
}




static int in_bounds(const Image *img, int row, int col) {
    return row >= 0 && row < img->height && col >= 0 && col < img->width;
}

static Pos *flood_fill(const Image *img, int row, int col, int *size) {
    uint32_t color = img->pixels[row][col];
    int total = img->width * img->height;
    char   *visited = calloc(total, 1);
    Pos    *stack   = malloc(total * sizeof(Pos));
    Pos    *result  = malloc(total * sizeof(Pos));
    int sp = 0, rp = 0;

    stack[sp++] = (Pos){row, col};
    visited[row * img->width + col] = 1;

    while (sp > 0) {
        Pos p = stack[--sp];
        result[rp++] = p;
        for (int d = 0; d < 4; d++) {
            int nr = p.row + DR[d];
            int nc = p.col + DC[d];
            if (in_bounds(img, nr, nc)
                    && !visited[nr * img->width + nc]
                    && img->pixels[nr][nc] == color) {
                visited[nr * img->width + nc] = 1;
                stack[sp++] = (Pos){nr, nc};
            }
        }
    }

    free(visited);
    free(stack);
    *size = rp;
    return result;
}

static Pos exit_codel(const Pos *block, int size, dir dp, dir cc) {

    int extreme = (dp == RIGHT || dp == DOWN) ? INT_MIN : INT_MAX;
    for (int i = 0; i < size; i++) {
        int v = (dp == RIGHT || dp == LEFT) ? block[i].col : block[i].row;
        if ((dp == RIGHT || dp == DOWN) ? v > extreme : v < extreme)
            extreme = v;
    }

    int want_max = (dp == RIGHT && cc == RIGHT)
                || (dp == DOWN  && cc == LEFT)
                || (dp == LEFT  && cc == LEFT)
                || (dp == UP    && cc == RIGHT);

    int sec = want_max ? INT_MIN : INT_MAX;
    Pos chosen = block[0];
    for (int i = 0; i < size; i++) {
        int prim = (dp == RIGHT || dp == LEFT) ? block[i].col : block[i].row;
        if (prim != extreme) continue;
        int s = (dp == RIGHT || dp == LEFT) ? block[i].row : block[i].col;
        if ((want_max && s > sec) || (!want_max && s < sec)) {
            sec = s;
            chosen = block[i];
        }
    }
    return chosen;
}


typedef void (*instruction_fn)(ProgramState *state, int block_size);

static void op_nop   (ProgramState *s, int sz) { (void)s; (void)sz; }
static void op_push  (ProgramState *s, int sz) { stack_push(s, sz); }
static void op_pop   (ProgramState *s, int sz) { int32_t a; (void)sz; stack_pop(s, &a); }

static void op_add(ProgramState *s, int sz) {
    int32_t a, b; (void)sz;
    if (stack_pop(s, &a) && stack_pop(s, &b)) stack_push(s, b + a);
}
static void op_sub(ProgramState *s, int sz) {
    int32_t a, b; (void)sz;
    if (stack_pop(s, &a) && stack_pop(s, &b)) stack_push(s, b - a);
}
static void op_mul(ProgramState *s, int sz) {
    int32_t a, b; (void)sz;
    if (stack_pop(s, &a) && stack_pop(s, &b)) stack_push(s, b * a);
}
static void op_div(ProgramState *s, int sz) {
    int32_t a, b; (void)sz;
    if (!stack_pop(s, &a) || !stack_pop(s, &b)) return;
    if (a == 0) { stack_push(s, b); stack_push(s, a); return; }
    stack_push(s, b / a);
}
static void op_mod(ProgramState *s, int sz) {
    int32_t a, b; (void)sz;
    if (!stack_pop(s, &a) || !stack_pop(s, &b)) return;
    if (a == 0) { stack_push(s, b); stack_push(s, a); return; }
    int32_t r = b % a;
    if (r != 0 && (r ^ a) < 0) r += a; /* result has same sign as divisor */
    stack_push(s, r);
}
static void op_not(ProgramState *s, int sz) {
    int32_t a; (void)sz;
    if (stack_pop(s, &a)) stack_push(s, a == 0 ? 1 : 0);
}
static void op_gt(ProgramState *s, int sz) {
    int32_t a, b; (void)sz;
    if (stack_pop(s, &a) && stack_pop(s, &b)) stack_push(s, b > a ? 1 : 0);
}
static void op_ptr(ProgramState *s, int sz) {
    int32_t n; (void)sz;
    if (!stack_pop(s, &n)) return;
    int steps = ((n % 4) + 4) % 4;
    for (int i = 0; i < steps; i++)
        s->DP = (dir)((s->DP + 1) % 4);
}
static void op_switch(ProgramState *s, int sz) {
    int32_t n; (void)sz;
    if (stack_pop(s, &n) && (n % 2) != 0)
        s->CC = (s->CC == LEFT) ? RIGHT : LEFT;
}
static void op_dup(ProgramState *s, int sz) {
    int32_t a; (void)sz;
    if (stack_pop(s, &a)) { stack_push(s, a); stack_push(s, a); }
}
static void op_roll(ProgramState *s, int sz) {
    int32_t n, d; (void)sz;
    if (!stack_pop(s, &n) || !stack_pop(s, &d)) return;
    if (d <= 0) return;
    int count = ((n % d) + d) % d;
    for (int i = 0; i < count; i++) {
        int32_t top = s->stack[s->stack_depth - 1];
        for (int j = s->stack_depth - 1; j > s->stack_depth - d; j--)
            s->stack[j] = s->stack[j - 1];
        s->stack[s->stack_depth - d] = top;
    }
}
static void op_in_c(ProgramState *s, int sz) {
    int c = getchar(); (void)sz;
    if (c != EOF) stack_push(s, (int32_t)c);
}
static void op_nuh_uh(ProgramState *s, int sz) {
    (void)s; (void)sz;
    printf("Removed for security reasons :3\n");
}
static void op_up(ProgramState *s, int sz) {
    (void)sz;
    s->stack_depth++;
}
static void op_down(ProgramState *s, int sz) {
    (void)sz;
    s->stack_depth--;
}

static const instruction_fn INSTRUCTIONS[6][3] = {
    { op_nop,     op_push,   op_pop    },
    { op_add,     op_sub,    op_mul    },
    { op_div,     op_mod,    op_not    },
    { op_gt,      op_ptr,    op_switch },
    { op_dup,     op_roll,   op_up     },
    { op_in_c,    op_nuh_uh, op_down   },
};

void doInstruction(int old_hex, int new_hex, int block_size, ProgramState *state) {
    color old_color = lookupColor(old_hex);
    color new_color = lookupColor(new_hex);
    if (old_color < 0 || new_color < 0) return; /* black, white, or unrecognized */

    int hue_step   = (hue(new_color)       - hue(old_color)       + 6) % 6;
    int light_step = (lightness(new_color) - lightness(old_color) + 3) % 3;

    INSTRUCTIONS[hue_step][light_step](state, block_size);
}

static int slide_white(const Image *img, int row, int col, dir dp,
                       int *out_row, int *out_col) {
    while (1) {
        int nr = row + DR[dp];
        int nc = col + DC[dp];
        if (!in_bounds(img, nr, nc) || img->pixels[nr][nc] == BLACK)
            return 0;
        if (img->pixels[nr][nc] != WHITE) {
            *out_row = nr;
            *out_col = nc;
            return 1;
        }
        row = nr;
        col = nc;
    }
}

int next_codel(const Image *img, ProgramState *state) {
    int size;
    int old_hex = img->pixels[state->row][state->col];
    Pos *block = flood_fill(img, state->row, state->col, &size);

    for (int attempt = 0; attempt < 8; attempt++) {
        Pos exit = exit_codel(block, size, state->DP, state->CC);
        int nr = exit.row + DR[state->DP];
        int nc = exit.col + DC[state->DP];

        if (!in_bounds(img, nr, nc) || img->pixels[nr][nc] == BLACK) {
            if (attempt % 2 == 0)
                state->CC = (state->CC == LEFT) ? RIGHT : LEFT;
            else
                state->DP = (dir)((state->DP + 1) % 4);
            continue;
        }

        if (img->pixels[nr][nc] == WHITE) {
            int dest_row, dest_col;
            if (!slide_white(img, nr, nc, state->DP, &dest_row, &dest_col)) {
                if (attempt % 2 == 0)
                    state->CC = (state->CC == LEFT) ? RIGHT : LEFT;
                else
                    state->DP = (dir)((state->DP + 1) % 4);
                continue;
            }
            state->row = dest_row;
            state->col = dest_col;
            free(block);
            /* white blocks are nops: no instruction executed */
            return 1;
        }
        int new_hex = img->pixels[nr][nc];
        state->row = nr;
        state->col = nc;
        free(block);
        doInstruction(old_hex, new_hex, size, state);
        return 1;
    }

    free(block);
    return 0;
}





void interpret_program(Image *img) {
    int32_t stack[256];
    ProgramState state = {
        .stack = stack,
        .stack_depth = 0,
        .CC = LEFT,
        .DP = RIGHT,
        .row = 0,
        .col = 0,
    };

    while (next_codel(img, &state)){
        color col = lookupColor(img->pixels[state.row][state.col]);
    }
    printf("halted\n");
}



int main(void) {
    setbuf(stdout, NULL);

    Image *img = load_png();
    if (!img) return 1;

    printf("Size: %d x %d\n", img->width, img->height);
    for (int y = 0; y < img->height; y++) {
        for (int x = 0; x < img->width; x++) {
            printf("%06X ", img->pixels[y][x]);
        }
        printf("\n");
    }
    interpret_program(img);
    free_image(img);
    return 0;
}
