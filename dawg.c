#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define FAILED 0xffffffff

// Dawg Structure
#define DAWG_MORE(x) (x & 0x80000000)
#define DAWG_LETTER(x) ((x >> 24) & 0x7f)
#define DAWG_LINK(x) (x & 0xffffff)

typedef unsigned int DawgRecord;

// Loading Functions
DawgRecord* dawg;

char* load_file(char* path) {
    FILE* file = fopen(path, "rb");
    fseek(file, 0, SEEK_END);
    int length = ftell(file);
    rewind(file);
    char* buffer = (char*)malloc(length);
    fread(buffer, 1, length, file);
    fclose(file);
    return buffer;
}

void init(char* dawgPath) {
    dawg = (DawgRecord*)load_file(dawgPath);
}

void uninit() {
    free(dawg);
}

// Dawg Functions
int get_dawg_record(DawgRecord* records, int index, char letter) {
    DawgRecord record;
    while (1) {
        record = records[index];
        if (DAWG_LETTER(record) == letter) {
            return index;
        }
        if (!DAWG_MORE(record)) {
            return FAILED;
        }
        index++;
    }
}

int is_word(char* letters) {
    int length = strlen(letters);
    int index = 0;
    for (int i = 0; i < length; i++) {
        index = get_dawg_record(dawg, index, letters[i]);
        if (index == FAILED) {
            return 0;
        }
        index = DAWG_LINK(dawg[index]);
    }
    return 1;
}

void get_children(char* result, char* letters) {
    int length = strlen(letters);
    int index = 0;
    for (int i = 0; i < length; i++) {
        index = get_dawg_record(dawg, index, letters[i]);
        if (index == FAILED) {
            result[0] = '\0';
            return;
        }
        index = DAWG_LINK(dawg[index]);
    }
    DawgRecord record;
    int i = 0;
    while (1) {
        record = dawg[index];
        result[i++] = DAWG_LETTER(record);
        if (!DAWG_MORE(record)) {
            result[i++] = '\0';
            return;
        }
        index++;
    }
}

int has_child(char* letters, char letter) {
    int length = strlen(letters);
    int index = 0;
    for (int i = 0; i < length; i++) {
        index = get_dawg_record(dawg, index, letters[i]);
        if (index == FAILED) {
            return 0;
        }
        index = DAWG_LINK(dawg[index]);
    }
    DawgRecord record;
    while (1) {
        record = dawg[index];
        if (letter == DAWG_LETTER(record)) {
            return 1;
        }
        if (!DAWG_MORE(record)) {
            return 0;
        }
        index++;
    }
}

// Grid Functions
int _find(char* grid, char* word, int* seen, int size, int length, int index, int x, int y) {
    if (x < 0 || y < 0 || x >= size || y >= size) {
        return 0;
    }
    int i = y * size + x;
    if (seen[i]) {
        return 0;
    }
    if (grid[i] != word[index]) {
        return 0;
    }
    if (grid[i] == 'q') {
        if (index == length - 1) {
            return 0;
        }
        if (word[index + 1] != 'u') {
            return 0;
        }
        index++;
    }
    if (index == length - 1) {
        return 1;
    }
    for (int dy = -1; dy <= 1; dy++) {
        for (int dx = -1; dx <= 1; dx++) {
            seen[i] = 1;
            int found = _find(grid, word, seen, size, length, index + 1, x + dx, y + dy);
            seen[i] = 0;
            if (found) {
                return 1;
            }
        }
    }
    return 0;
}

int find(char* grid, char* word) {
    int length = strlen(word);
    int size;
    switch (strlen(grid)) {
        case 16: size = 4; break;
        case 25: size = 5; break;
        default: return 0;
    }
    int* seen = calloc(size * size, sizeof(int));
    for (int y = 0; y < size; y++) {
        for (int x = 0; x < size; x++) {
            int found = _find(grid, word, seen, size, length, 0, x, y);
            if (found) {
                free(seen);
                return 1;
            }
        }
    }
    free(seen);
    return 0;
}
