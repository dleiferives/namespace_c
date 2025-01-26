


// TODO @(dleiferives,5e7b1b5c-f78d-4ff0-811d-680bb0ef544b): add support for
// nested structs / namespaces :dcc: ~#

struct primary{
    secondary a;
    primary *b;
    secondary @c;
    primary @d;

    int @func(primary *self, secondary b){
        return 10;
    };

    void *@bunc(primary *self){
        return;
    };

};

struct secondary{
    primary a;
    secondary *b;

    int @func(primary *self, secondary b){
        return 10;
    };
};
