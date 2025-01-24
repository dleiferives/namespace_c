#include <stdio.h>

// int globalVar = 42;
// float globalFloat;
// char *globalString = "Hello, World!";
// const unsigned int globalArray[10] = {0};
// double *globalPointer;

typedef struct OtherType_s OtherType;
struct OtherType_s {
    int x;
};


int OtherType_increment(int value) {
    return value + 1;
}




typedef struct MyType_s MyType;
struct MyType_s {
    int x;
};

typedef struct MyType_globals_s MyType_globals_t;
struct MyType_globals_s {
    // this is a global comment!
    int y;
};
MyType_globals_t MyType_globals;


int MyType_add(MyType *self, int a) {
    self->x += a;
        return self->x;
}

// this is a test comment
// this is another one!
int MyType_increment(int value) {
    return value + 1;
}

// this is a second test comment
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
    //MyType_add(b, (MyType_globals.y)->a.b);
    MyType_add(b, (MyType_globals.y));
    MyType_add(b,20);
}

int add(int d, int b) {
    OtherType *a;
    OtherType_increment(20);
    int sum = d + b;
    return sum;
}

int main(){
    OtherType a;
    OtherType_increment(10);
    return 0;
}

///////////////////////////////////////
// main.d source pre transform
// #include <stdio.h>
// 
// // int globalVar = 42;
// // float globalFloat;
// // char *globalString = "Hello, World!";
// // const unsigned int globalArray[10] = {0};
// // double *globalPointer;
// 
// struct OtherType{
// 	int x;
// 	int @increment(int value){
// 		return value + 1;
// 	};
// };
// 
// 
// struct MyType {
//     int x;
//     // this is a global comment!
//     int @y;
//     int @add(MyType *self, int a) {
//         self->x += a;
//         return self->x;
//     };
// 
//     // this is a test comment
//     // this is another one!
//     int @increment(int value) {
//         return value + 1;
//     };
//     // this is a second test comment
//     int @global_increment(int value) {
//         return value + MyType@y;
//     };
// };
// 
// void myFunction() {
//     int localVar = 10;
//     if (localVar > 5) {
//         int innerIfVar = 20;
//         if (innerIfVar > 15) {
//             int nestedIfVar = 30;
//         }
//     }
//     for (int i = 0; i < 10; i++) {
//         float loopVar = 3.14;
//         for (int j = 0; j < 5; j++) {
//             int nestedForVar = 50;
//         }
//     }
//     MyType a;
//     a@increment(10);
//     a@add(5);
//     MyType *b;
//     //b@add(MyType@y->a.b);
//     b@add(MyType@y);
//     MyType@add(b,20);
// }
// 
// int add(int d, int b) {
//     OtherType *a;
//     a@increment(20);
//     int sum = d + b;
//     return sum;
// }
// 
// int main(){
//     OtherType a;
//     a@increment(10);
//     return 0;
// }
