!start.

gun(snipper)[role(snipper)].

+!start: gun(snipper) & gun(snipper)
<-
    //.send(executer,achieve,attack);
    //.wait(1000);
    //.send(executer,delRole,tank);
    //.send(executer,addRole,support);
    .send(executer,updateRole,[tank,snipper]);
    .send(executer, tellRole, snipper);
    //.send(executer, tell, hola(mundo));
    .wait(3000);
    .send(executer,achieve,shoot).

@p1 [role(snipper)]
+!shoot: role(snipper) & gun(snipper)
<-
    .print("Bang").

