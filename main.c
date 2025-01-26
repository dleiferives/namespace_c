#include <stdio.h>

// int globalVar = 42;
// float globalFloat;
// char *globalString = "Hello, World!";
// const unsigned int globalArray[10] = {0};
// double *globalPointer;

typedef struct Type3_globals_s Type3_globals_t;
struct Type3_globals_s {
    
    int g1;
};
Type3_globals_t Type3_globals;

// smoko
int Type3_f1() {
    return 1;
}


typedef struct OtherType_s OtherType_t;
struct OtherType_s {
    int x;
};


int OtherType_increment(int value) {
    return value + 1;
}




typedef struct MyType_s MyType_t;
struct MyType_s {
    int ***x;
    MyType_t *ref;
};

typedef struct MyType_globals_s MyType_globals_t;
struct MyType_globals_s {
    // this is a global comment!
    unsigned int y;
    int ****x;
};
MyType_globals_t MyType_globals;


int MyType_add(MyType_t *self, int a) {
    self->x += a;
        return self->x;
}

// this is a test comment
// this is another one!
int MyType_increment(int value) {
    return value + 1;
}



MyType_t *MyType_get(MyType_t *self, ) {
    return self;
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
    MyType_t a;
    MyType_increment(10);
    MyType_add(&a, 5);
    MyType_t *b = MyType_get(&a);
    //MyType_add(b, (MyType_globals.y)->a.b);
    MyType_add(b, (MyType_globals.y));
    MyType_add(b,20);
}

int add(int d, int b) {
    OtherType_t *a;
    OtherType_increment(20);
    int sum = d + b;
    return sum;
}

int main(){
    OtherType_t a;
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
// struct Type3{
//     int @g1;
// 
//     //
// 
//     // smoko
//     int @f1(){
//         return 1;
//     };
// 
// };
// struct OtherType{
// 	int x;
// 	int @increment(int value){
// 		return value + 1;
// 	};
// };
// 
// 
// struct MyType {
//     int ***x;
//     // this is a global comment!
//     unsigned int @y;
//     int ****@x;
//     MyType *ref;
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
// 
//     MyType *@get(MyType *self){
//         return self;
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
//     MyType *b = a@get();
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
