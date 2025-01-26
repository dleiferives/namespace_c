
typedef struct Casted_s Casted_t;
struct Casted_s {
     int a;
     int b;
};

typedef struct Casted_globals_s Casted_globals_t;
struct Casted_globals_s {
     int c;
};
Casted_globals_t Casted_globals;


int Casted_d() {
    return (Casted_globals.c);
}


Casted_t Casted_aself(Casted_t *self, ) {
    return (Casted_t)self->a;
}



int main(){
    int *l;
    Casted_t m;
    m.a = 10;
    l = (int*)&m;
    Casted_t n = *((Casted_t*)l);
}

///////////////////////////////////////
// test_typecasts.c autogenerated from test_typecasts.d: 
// 
// struct Casted{
//     int a;
//     int b;
//     int @c;
//     int @d(){
//         return Casted@c;
//     };
//     Casted @aself(Casted *self){
//         return (Casted)self->a;
//     };
// };
// 
// 
// int main(){
//     int *l;
//     Casted m;
//     m.a = 10;
//     l = (int*)&m;
//     Casted n = *((Casted*)l);
// }
