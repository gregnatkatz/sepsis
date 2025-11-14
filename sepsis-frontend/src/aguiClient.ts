
interface AGUIEvent {
  id: string
  type: string
  sessionId: string
  ts: string
  payload: any
}

type EventHandler = (event: AGUIEvent) => void

export class AGUIClient {
  private ws: WebSocket | null = null
  private sessionId: string | null = null
  private token: string | null = null
  private eventHandlers: Map<string, EventHandler[]> = new Map()
  private apiUrl: string

  constructor(apiUrl: string) {
    this.apiUrl = apiUrl
  }

  async createSession(patientId?: string): Promise<void> {
    const response = await fetch(`${this.apiUrl}/api/agui/session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ patient_id: patientId })
    })

    if (!response.ok) {
      throw new Error('Failed to create AG-UI session')
    }

    const data = await response.json()
    this.sessionId = data.sessionId
    this.token = data.token
  }

  async connect(): Promise<void> {
    if (!this.token) {
      throw new Error('No session token. Call createSession() first.')
    }

    return new Promise((resolve, reject) => {
      const wsProtocol = this.apiUrl.startsWith('https') ? 'wss:' : 'ws:'
      const wsHost = this.apiUrl.replace(/^https?:\/\//, '')
      const wsUrl = `${wsProtocol}//${wsHost}/api/agui/ws?token=${this.token}`

      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        console.log('AG-UI WebSocket connected')
      }

      this.ws.onmessage = (event) => {
        try {
          const aguiEvent: AGUIEvent = JSON.parse(event.data)
          
          if (aguiEvent.type === 'session.ready') {
            resolve()
          }

          this.triggerHandlers(aguiEvent.type, aguiEvent)
          this.triggerHandlers('*', aguiEvent) // Wildcard handlers
        } catch (error) {
          console.error('Error parsing AG-UI event:', error)
        }
      }

      this.ws.onerror = (error) => {
        console.error('AG-UI WebSocket error:', error)
        reject(error)
      }

      this.ws.onclose = () => {
        console.log('AG-UI WebSocket closed')
        this.triggerHandlers('connection.closed', {
          id: '',
          type: 'connection.closed',
          sessionId: this.sessionId || '',
          ts: new Date().toISOString(),
          payload: {}
        })
      }
    })
  }

  send(eventType: string, payload: any): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.error('AG-UI WebSocket not connected')
      return
    }

    const event = {
      type: eventType,
      sessionId: this.sessionId,
      payload
    }

    this.ws.send(JSON.stringify(event))
  }

  on(eventType: string, handler: EventHandler): void {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, [])
    }
    this.eventHandlers.get(eventType)!.push(handler)
  }

  off(eventType: string, handler?: EventHandler): void {
    if (!handler) {
      this.eventHandlers.delete(eventType)
    } else {
      const handlers = this.eventHandlers.get(eventType)
      if (handlers) {
        const index = handlers.indexOf(handler)
        if (index > -1) {
          handlers.splice(index, 1)
        }
      }
    }
  }

  private triggerHandlers(eventType: string, event: AGUIEvent): void {
    const handlers = this.eventHandlers.get(eventType)
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(event)
        } catch (error) {
          console.error(`Error in AG-UI event handler for ${eventType}:`, error)
        }
      })
    }
  }

  close(): void {
    if (this.ws) {
      this.send('session.close', {})
      this.ws.close()
      this.ws = null
    }
    this.sessionId = null
    this.token = null
    this.eventHandlers.clear()
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }

  getSessionId(): string | null {
    return this.sessionId
  }
}
