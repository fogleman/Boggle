#include <stdio.h>
#include <stdlib.h>

#define FAILED 0xffffffff

// Dawg Structure
#define DAWG_MORE(x) (x & 0x80000000)
#define DAWG_LETTER(x) ((x >> 24) & 0x7f)
#define DAWG_LINK(x) (x & 0xffffff)

typedef unsigned int DawgRecord;

// Loading Functions
DawgRecord* dawg;

char* loadFile(char* path) {
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
    dawg = (DawgRecord*)loadFile(dawgPath);
}

void uninit() {
    free(dawg);
}

// Dawg Functions
int getDawgRecord(DawgRecord* records, int index, char letter) {
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

void getChildren(char* result, char* letters, int length) {
    int index = 0;
    for (int i = 0; i < length; i++) {
        index = getDawgRecord(dawg, index, letters[i]);
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

int hasChild(char letter, char* letters, int length) {
    int index = 0;
    for (int i = 0; i < length; i++) {
        index = getDawgRecord(dawg, index, letters[i]);
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
