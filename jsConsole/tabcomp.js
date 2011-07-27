 function TabComplete(cursorEl, buffer){
                var self = this;
                this.active = false;
                this.list = $("<ul>", {"class":"tabList"}).css({"position": "absolute"});
                $("body").append(this.list);
                
                this.render = function(words){
                    self.list.css("left", cursorEl.offset().left +  "px" )
                    self.list.css("top", cursorEl.height() + cursorEl.offset().top + "px" );
                    for(var i = 0; i < words.length; i++){
                        self.list.append($("<li>").text(words[i]));
                    }
                    self.list.show();
                }
                
                this.directions = [{ cmd: "east" },{ cmd: "west" },{ cmd: "north" },{ cmd: "south" } ];
                
                //Command Tree has been structured in such a way that you HAVE to type one letter before
                //you can get autocompletion.
                this.commandTree = {
                    w : [{ cmd: "walk" , subs : this.directions },{ cmd: "watch" }]
                    , s : [{ cmd: "say" }, { cmd: "start" }, {cmd : "sing" } ]
                    , g : [{  cmd: "go", subs: this.directions }, { cmd: "get" }]
                };
                this.close = function(){
                    self.list.empty();
                    self.active = false;
                }
                this.scanBranch = function(branch, needles){
                    var suspects = [];
                    if(needles[0] == ""){
                        for(var b = 0; b < branch.length; b++){
                            suspects.push(branch[b].cmd);
                        }
                    }
                    else if(needles.length > 1 ){
                        var dbg = null;
                        //We already have a sentenance, just need to complete it
                        for(var b = 0; b < branch.length; b++){
                            if(branch[b].cmd.startswith(needles[0]) && typeof branch[b].subs != "undefined" ) {
                                suspects = suspects.concat( dbg = this.scanBranch( branch[b].subs, needles.slice(1) ) );
                            }
                        }
                        
                    }
                    else{
                        //We're at the beginning of the end
                        for(var b = 0; b < branch.length; b++ ){
                            if(branch[b].cmd.startswith(needles[0]) ){
                                suspects.push(branch[b].cmd);
                            }
                        }
                    }
                    return suspects;
                    
                }
                
                this.seek = function(){
                    var suspects = []
                    self.list.empty();
                    var needles = buffer._raw.replace("&nbsp;", " ").split(" ")
               
                    
                    if( needles.length > 0 && typeof self.commandTree[needles[0][0]] != "undefined"  ){  
                        var suspects = self.scanBranch( self.commandTree[needles[0][0]], needles );
                    }
                   
                    if(suspects.length === 1)
                    {
                        var word = suspects[0];
                        buffer._raw += word.slice(needles.slice(-1)[0].length);
                        self.close();
                        
                    }
                    else if(suspects.length > 1){
                        self.render(suspects);
                        self.active = true;
                    }else{
                        self.close();
                    }
                }
                
                
            }