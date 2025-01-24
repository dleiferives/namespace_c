#include <stdio.h>

int globalVar = 42;
float globalFloat;
char *globalString = "Hello, World!";
const unsigned int globalArray[10] = {0};
double *globalPointer;

typedef struct MyType_s MyType;
struct MyType_s {
    int x;
};

typedef struct MyType_globals_s MyType_globals_t;
struct MyType_globals_s {
    int y;
};
MyType_globals_t MyType_globals;

int MyType_add(MyType *self, int a) {
    self->x += a;
        return self->x;
}

int MyType_increment(int value) {
    return value + 1;
}

int MyType_global_increment(int value) {
    return value + (MyType_globals.y);
}



void myFunction() {
    int localVar = 10;
    if (localVar > 5) {
        int innerIfVar = 20;
        if (innerIfVar > 15) {
            int nestedIfVar = 30;
        }
    }
    for (int i = 0; i < 10; i++) {
        float loopVar = 3.14;
        for (int j = 0; j < 5; j++) {
            int nestedForVar = 50;
        }
    }
    MyType a;
    MyType_increment(10);
    MyType_add(&a, 5);
    MyType *b;
    MyType_add(b, (MyType_globals.y)->a.b);
    MyType_add(b,20);
}

int add(int a, int b) {
    int sum = a + b;
    return sum;
}
