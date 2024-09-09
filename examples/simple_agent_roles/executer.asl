!start.

role(tank).

+!start 
<-
    .wait(100);
    !start.

+!attack: role(tank)
<-
    .print("attack").

+!heal: role(support)
<- 
    .print("heal").

+!attack.

+!heal.