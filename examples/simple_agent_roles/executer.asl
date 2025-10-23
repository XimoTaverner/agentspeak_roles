//!start.

role([tank]).

+!start 
<-
    .wait(100);
    //.send(dispatcher,askHow,"+!shoot");
    //!start.
    !attack.


@p1[role([tank])]
+!attack: role(X) 
<-
    .printbeliefs;
    .print("attack").

@p2[role([snipper])]
+!attack: role(X)
<- 
    .printbeliefs;
    .print("heal").

+!attack
<-
    .printbeliefs;
    .print("MAL").

+!heal.