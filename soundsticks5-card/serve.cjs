// Local visual-review server; serves files from this study directory only.
const http=require('node:http');
const fs=require('node:fs');
const path=require('node:path');
const types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.md':'text/plain; charset=utf-8','.svg':'image/svg+xml','.png':'image/png'};
http.createServer((req,res)=>{
  const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const file=path.resolve(__dirname,'.'+(pathname==='/'?'/preview.html':pathname));
  if(!file.startsWith(__dirname+path.sep)){res.writeHead(403);res.end();return;}
  fs.readFile(file,(error,data)=>{
    if(error){res.writeHead(404);res.end('Not found');return;}
    res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream','Cache-Control':'no-store'});res.end(data);
  });
}).listen(8769,'127.0.0.1',()=>process.stdout.write('SoundSticks visual study: http://127.0.0.1:8769\n'));
