//!start.

role(tank).

ataque(chungo)[role(tank)].

+!start 
<-
    .wait(100);
    //.send(dispatcher,askHow,"+!shoot");
    !start.

+!attack: role(tank)
<-
    .print("attack").

+!heal: role(support)
<- 
    .print("heal").

+!attack.

+!heal.