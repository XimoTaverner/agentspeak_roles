!start.

gun(snipper)[role(snipper)].

+!start
<-
    .send(executer,achieve,attack);
    .wait(1000);
    //.send(executer,delRole,tank);
    //.send(executer,addRole,support);
    //.send(executer,updateRole,[support,tank]);
    .send(executer, tellRole, snipper);
    .wait(1000);
    .send(executer,achieve,attack).

@p1 [role(snipper)]
+!shoot: role(snipper)
<-
    print("Bang").

@p2 [role(snipper)]
+!shoot.