import React from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FileCode2, Terminal, Network } from "lucide-react";

export default function Inspector() {
  return (
    <div className="w-[280px] h-full bg-card border-l border-border flex flex-col flex-shrink-0">
      <Tabs defaultValue="artifacts" className="flex-1 flex flex-col">
        <div className="px-4 py-3 border-b border-border">
          <TabsList className="w-full grid grid-cols-3 bg-background">
            <TabsTrigger value="artifacts" className="text-xs py-1.5"><FileCode2 className="w-3 h-3 mr-1.5" />Artifacts</TabsTrigger>
            <TabsTrigger value="sources" className="text-xs py-1.5"><Network className="w-3 h-3 mr-1.5" />Sources</TabsTrigger>
            <TabsTrigger value="terminal" className="text-xs py-1.5"><Terminal className="w-3 h-3 mr-1.5" />Terminal</TabsTrigger>
          </TabsList>
        </div>
        
        <TabsContent value="artifacts" className="flex-1 p-0 m-0 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="p-4 space-y-4">
              <div className="text-sm text-muted-foreground text-center py-8">
                No artifacts generated yet.
              </div>
            </div>
          </ScrollArea>
        </TabsContent>
        
        <TabsContent value="sources" className="flex-1 p-0 m-0 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="p-4 space-y-4">
              <div className="text-sm text-muted-foreground text-center py-8">
                No sources loaded.
              </div>
            </div>
          </ScrollArea>
        </TabsContent>
        
        <TabsContent value="terminal" className="flex-1 p-0 m-0 overflow-hidden">
          <div className="h-full p-4">
            <div className="h-full bg-black rounded border border-border p-3 font-mono text-xs overflow-auto text-green-400">
              <div className="opacity-50"># Midday Workbench Sandbox</div>
              <div className="opacity-50">$ waiting for commands...</div>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
