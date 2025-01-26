struct Goomba{
    int @member(){
        return 10;
    };
};


int main(){
    void * a = &Goomba@member;
}
