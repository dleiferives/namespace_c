
struct Casted{
    int a;
    int b;
    int @c;
    // TODO @(dleiferives,c39474d0-2519-40cf-8d23-4f87a057ef34): explicitly add
    // void to generated member functions without any args ~#
    int @d(){
        return Casted@c;
    };
    Casted @aself(Casted *self){
        return (Casted)self->a;
    };
};


int main(){
    int *l;
    Casted m;
    m.a = 10;
    l = (int*)&m;
    Casted n = *((Casted*)l);
}
