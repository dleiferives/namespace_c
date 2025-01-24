#include <stdio.h>

// int globalVar = 42;
// float globalFloat;
// char *globalString = "Hello, World!";
// const unsigned int globalArray[10] = {0};
// double *globalPointer;

struct OtherType{
	int x;
	int @increment(int value){
		return value + 1;
	};
};


struct MyType {
    int x;
    int @y;
    int @add(MyType *self, int a) {
        self->x += a;
        return self->x;
    };

    int @increment(int value) {
        return value + 1;
    };
    int @global_increment(int value) {
        return value + MyType@y;
    };
};

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
    a@increment(10);
    a@add(5);
    MyType *b;
    //b@add(MyType@y->a.b);
    b@add(MyType@y);
    MyType@add(b,20);
}

int add(int d, int b) {
    OtherType *a;
    a@increment(20);
    int sum = d + b;
    return sum;
}

int main(){
    OtherType a;
    a@increment(10);
    return 0;
}
