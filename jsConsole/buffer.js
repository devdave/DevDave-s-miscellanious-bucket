function Buffer(log, consoleEl, cursorEl){
                var self = this;
                this._raw = "";
                this.prefix = "You Typed:\n";
                this.tabComp = new TabComplete(cursorEl, self);
                
                
                this.override = function bufOver(input){
                    self._raw = unescape(input.replace(self.prefix, ""));
                    this.update();
                }
                
                this.update = function bufUp(){
                    consoleEl.html(self._raw);
                }
                
                this.processCtrl = function ctrlProcess(which){
                    switch(which){
                        case 8:
                            if(/&nbsp;$/.test(self._raw)){
                                self._raw = self._raw.slice(0, - "&nbsp;".length );
                            }else{
                                self._raw = self._raw.slice(0,-1);    
                            }
                            
                            break;
                        case 9:
                            self.tabComp.seek();
                            break;
                        case 13:
                            log.append($("<div>", {"class":"log_entry"} ).html(self.prefix + self._raw))
                            self._raw = "";
                            break;
                        case 32:
                            self._raw += "&nbsp;";
                    }
                    
                        
                }
                this.process = function bufProcess(which){
                    self._raw += String.fromCharCode(which);
                    if(self.tabComp.active){
                        self.tabComp.seek()
                    }

                }
                
                
                this.handlePress = function(evt){
                    if(evt.which > 32){
                        self.process(evt.which);                    
                        evt.stopPropagation();
                        self.update();
                        return false;
                    }
                    
                }
                this.ctrlCode = function(evt){
                    if(evt.which <= 32){
                        self.processCtrl(evt.which);
                    
                        evt.stopPropagation();
                        self.update();
                        return false;
                    }
                }
                
            }