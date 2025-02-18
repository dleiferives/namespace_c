typedef struct Space_s Space_t;
struct Space_s {
     int a;
};



int Space_alone(Space_t *self) {
    return self->a;
}



int Space_together(Space_t *self, Space_t *other) {
    return self->a;
}



int Space_switched(Space_t *other, Space_t *self) {
    return self->a;
}


int main(){
    Space_t the_final_frontier;
    Space_t is_cold;
    the_final_frontier.a = 20;
    is_cold.a = 30;
    if(Space_alone(&the_final_frontier) != 20) exit(1);
    if(Space_together(&is_cold, &the_final_frontier) != 30) exit(1);
    if(Space_switched(&the_final_frontier) != 20) exit(1);

    return 0;
}

///////////////////////////////////////
// test_member_function_args.c autogenerated from test_member_function_args.d: 
// struct Space{
//     int a;
// 
//     int @alone(Space * self){
//         return self->a;
//     };
// 
//     int @together(Space *self, Space *other){
//         return self->a;
// 
//     };
// 
//     int @switched(Space *other, Space *self){
//         return self->a;
//     };
// 
// };
// 
// int main(){
//     Space the_final_frontier;
//     Space is_cold;
//     the_final_frontier.a = 20;
//     is_cold.a = 30;
//     if(the_final_frontier@alone() != 20) exit(1);
//     if(is_cold@together(&the_final_frontier) != 30) exit(1);
//     if(is_cold@switched(&the_final_frontier) != 20) exit(1);
// 
//     return 0;
// }
