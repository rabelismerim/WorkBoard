export function subscribeWorkspace(onChange, onStatus) {
  let socket, retry, heartbeat, stopped=false, delay=1000
  function connect() {
    if(stopped)return
    onStatus('connecting')
    socket=new WebSocket(`${location.protocol==='https:'?'wss:':'ws:'}//${location.host}/ws/workspace/`)
    socket.onopen=()=>{delay=1000;onStatus('connected');onChange();heartbeat=setInterval(()=>socket.readyState===WebSocket.OPEN && socket.send(JSON.stringify({type:'ping'})),30000)}
    socket.onmessage=event=>{try{if(JSON.parse(event.data).type==='workspace.changed')onChange()}catch{}}
    socket.onclose=event=>{clearInterval(heartbeat);onStatus('offline');if(!stopped && event.code!==4401){retry=setTimeout(connect,delay);delay=Math.min(delay*2,30000)}}
  }
  connect()
  return ()=>{stopped=true;clearTimeout(retry);clearInterval(heartbeat);socket?.close()}
}
