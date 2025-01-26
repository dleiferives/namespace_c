struct Space{
    int a;

    int @alone(Space * self){
        return self->a;
    };

    int @together(Space *self, Space *other){
        return self->a;

    };

    int @switched(Space *other, Space *self){
        return self->a;
    };

};

// TODO @(dleiferives,094df03c-85fe-439c-8ac2-582c7918eb9a): Figure out what to do
// if a struct with no member values uses itself. ~#
// IDEA @(dleiferives,44a0007d-8ca0-4e32-a673-22400b3e7be6): Could just make a
// struct with no members. if that does not compile then its possible to just add
// one. ~#
struct Empty{
    Empty @nothing(Empty *self){
        return *self;
    };
}

int main(){
    Space the_final_frontier;
    Space is_cold;
    the_final_frontier.a = 20;
    is_cold.a = 30;
    if(the_final_frontier@alone() != 20) exit(1);
    if(is_cold@together(&the_final_frontier) != 30) exit(1);
    // TODO @(dleiferives,25bce2d9-851f-4557-8892-dca625b5843d): add compiler
    // errors for when number of arguments passed does not align with arguments
    // used ~#
    // TODO @(dleiferives,83f65d32-7687-49eb-8294-28dd7a71e12d): emacs todo remove
    // org mode addition for note, info, make answer have to be on a question.
    // adds to the org mode entry for the question and marks it answered or
    // something. removde duplication of text ~#
    // NOTE @(dleiferives,16ad7ac7-86d9-460d-946a-dc465cf2c085): This is intended
    // to error ~#
    if(is_cold@switched(&the_final_frontier) != 20) exit(1);

    return 0;
}
