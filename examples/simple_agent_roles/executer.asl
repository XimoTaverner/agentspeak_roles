role([tank]).

@p1[role([tank])]
+!attack: role(X) 
<-
    .print("attack").

@p2[role([snipper])]
+!attack: role(X)
<- 
    .print("heal").

+!attack
<-
    .print("general").
