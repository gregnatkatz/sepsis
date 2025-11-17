import { useState, useEffect, useRef } from 'react'
import './App.css'
import { Mic, MicOff, Activity, AlertTriangle, Users, Table as TableIcon, MessageSquare, Search, TrendingUp, Brain, Beaker, Stethoscope, Thermometer, Clock, CheckCircle2, BarChart3 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, BarChart, Bar } from 'recharts'
import { AGUIClient } from './aguiClient'

const API_URL = (import.meta.env.VITE_API_URL && import.meta.env.VITE_API_URL.trim() !== '') 
  ? import.meta.env.VITE_API_URL 
  : window.location.origin

const API_AUTH = import.meta.env.VITE_API_AUTH || ''

const getAuthHeaders = () => {
  const headers: Record<string, string> = {
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
  }
  if (API_AUTH) {
    headers['Authorization'] = API_AUTH
  }
  return headers
}

const USE_AGUI = new URLSearchParams(window.location.search).get('agui') === '1' ||
                 import.meta.env.VITE_USE_AGUI === 'true'

interface Patient {
  id: string
  mrn: string
  name: string
  room: string
  age: number
  gender: string
  admission_date: string
  diagnosis: string
  risk_score: number
  risk_level: string
  sirs_criteria: number
  vitals: {
    current: {
      heart_rate: number
      respiratory_rate: number
      temperature: number
      blood_pressure: string
      spo2: number
    }
    previous: {
      heart_rate: number
      respiratory_rate: number
      temperature: number
      blood_pressure: string
      spo2: number
    }
  }
  labs: {
    current: {
      wbc: number
      lactate: number
      creatinine: number
      bilirubin: number
    }
    previous: {
      wbc: number
      lactate: number
      creatinine: number
      bilirubin: number
    }
  }
  devices: Array<{ type: string; days: number }>
  notes: Array<{ time: string; note: string }>
}

function App() {
  const [patients, setPatients] = useState<Patient[]>([])
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null)
  const [currentView, setCurrentView] = useState<'dashboard' | 'table' | 'chat' | 'rl-analytics' | 'report'>('dashboard')
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [chatMessages, setChatMessages] = useState<Array<{ role: string; content: string }>>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [sortColumn, setSortColumn] = useState<string>('risk_score')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  const [filterRisk, setFilterRisk] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [quickViewOpen, setQuickViewOpen] = useState(false)
  const [quickViewPatient, setQuickViewPatient] = useState<Patient | null>(null)
  const [patientHistory, setPatientHistory] = useState<any[]>([])
  const [aiInsights, setAiInsights] = useState<any>(null)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [loadingAnalysis, setLoadingAnalysis] = useState(false)
  const [horizonForecast, setHorizonForecast] = useState<any>(null)
  const [nextBestAction, setNextBestAction] = useState<any>(null)
  const [sepsisBundle, setSepsisBundle] = useState<any>(null)
  const [earlyWarning, setEarlyWarning] = useState<any>(null)
  const [whatIfIntervention, setWhatIfIntervention] = useState<any>({
    fluids_ml: 0,
    oxygen_increase: 0,
    antibiotics_given: false,
    vasopressors_started: false
  })
  const [whatIfPrediction, setWhatIfPrediction] = useState<any>(null)
  const [loadingGameChangers, setLoadingGameChangers] = useState(false)
  const [loadingWhatIf, setLoadingWhatIf] = useState(false)
  const [rlResults, setRlResults] = useState<any>(null)
  const [loadingRlResults, setLoadingRlResults] = useState(false)
  const [monteCarloPathways, setMonteCarloPathways] = useState<any>(null)
  const [selectedPathway, setSelectedPathway] = useState<number>(0)
  const [loadingMonteCarlo, setLoadingMonteCarlo] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const mediaStreamRef = useRef<MediaStream | null>(null)
  const aguiClientRef = useRef<AGUIClient | null>(null)

  useEffect(() => {
    fetchPatients()
  }, [])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  useEffect(() => {
    if (currentView === 'rl-analytics' && !rlResults && !loadingRlResults) {
      fetchRlResults()
    }
  }, [currentView])

  const fetchPatients = async () => {
    try {
      const response = await fetch(`${API_URL}/api/patients`, {
        headers: getAuthHeaders()
      })
      const data = await response.json()
      setPatients(data.patients)
    } catch (error) {
      console.error('Error fetching patients:', error)
    }
  }

  const fetchRlResults = async () => {
    setLoadingRlResults(true)
    try {
      const response = await fetch(`${API_URL}/api/rl/results`, {
        headers: getAuthHeaders()
      })
      const data = await response.json()
      setRlResults(data)
    } catch (error) {
      console.error('Error fetching RL results:', error)
    } finally {
      setLoadingRlResults(false)
    }
  }

  const connectToRealtimeAPI = async () => {
    try {
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${wsProtocol}//${window.location.host}/api/realtime`
      
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws
      
      ws.onopen = async () => {
        console.log('Connected to Realtime API')
        
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        mediaStreamRef.current = stream
        
        const audioContext = new AudioContext({ sampleRate: 24000 })
        audioContextRef.current = audioContext
        
        const source = audioContext.createMediaStreamSource(stream)
        const processor = audioContext.createScriptProcessor(4096, 1, 1)
        
        processor.onaudioprocess = (e) => {
          const inputData = e.inputBuffer.getChannelData(0)
          const pcm16 = new Int16Array(inputData.length)
          for (let i = 0; i < inputData.length; i++) {
            pcm16[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768))
          }
          const base64Audio = btoa(String.fromCharCode(...new Uint8Array(pcm16.buffer)))
          
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
              type: 'input_audio_buffer.append',
              audio: base64Audio
            }))
          }
        }
        
        source.connect(processor)
        processor.connect(audioContext.destination)
        
        ws.send(JSON.stringify({
          type: 'session.update',
          session: {
            modalities: ['text', 'audio'],
            instructions: 'You are a clinical AI assistant helping with sepsis prevention. Provide concise, evidence-based recommendations.',
            voice: 'alloy',
            input_audio_format: 'pcm16',
            output_audio_format: 'pcm16',
            turn_detection: {
              type: 'server_vad',
              threshold: 0.5,
              prefix_padding_ms: 300,
              silence_duration_ms: 500
            }
          }
        }))
      }
      
      ws.onmessage = (event) => {
        const message = JSON.parse(event.data)
        
        if (message.type === 'response.audio.delta') {
          const audioData = atob(message.delta)
          const pcm16 = new Int16Array(audioData.length / 2)
          for (let i = 0; i < pcm16.length; i++) {
            pcm16[i] = (audioData.charCodeAt(i * 2) | (audioData.charCodeAt(i * 2 + 1) << 8))
          }
          
          if (audioContextRef.current) {
            const audioBuffer = audioContextRef.current.createBuffer(1, pcm16.length, 24000)
            audioBuffer.getChannelData(0).set(pcm16.map(v => v / 32768))
            const source = audioContextRef.current.createBufferSource()
            source.buffer = audioBuffer
            source.connect(audioContextRef.current.destination)
            source.start()
          }
        } else if (message.type === 'response.text.delta') {
          setChatMessages(prev => {
            const last = prev[prev.length - 1]
            if (last && last.role === 'assistant') {
              return [...prev.slice(0, -1), { ...last, content: last.content + message.delta }]
            }
            return [...prev, { role: 'assistant', content: message.delta }]
          })
        } else if (message.type === 'conversation.item.input_audio_transcription.completed') {
          setTranscript(message.transcript)
          setChatMessages(prev => [...prev, { role: 'user', content: message.transcript }])
        }
      }
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
      
      ws.onclose = () => {
        console.log('Disconnected from Realtime API')
        if (mediaStreamRef.current) {
          mediaStreamRef.current.getTracks().forEach(track => track.stop())
        }
        if (audioContextRef.current) {
          audioContextRef.current.close()
        }
      }
    } catch (error) {
      console.error('Error connecting to Realtime API:', error)
    }
  }

  const toggleVoiceRecognition = () => {
    if (isListening) {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      setIsListening(false)
    } else {
      connectToRealtimeAPI()
      setIsListening(true)
    }
  }

  const handleSendMessage = async (message: string) => {
    if (!message.trim()) return
    
    setChatMessages(prev => [...prev, { role: 'user', content: message }])
    setTranscript('')
    
    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message })
      })

      if (!response.ok) throw new Error('Failed to get response')

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let assistantMessage = ''
      
      setIsStreaming(true)
      setChatMessages(prev => [...prev, { role: 'assistant', content: '' }])

      while (reader) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.content) {
                assistantMessage += data.content
                setChatMessages(prev => {
                  const newMessages = [...prev]
                  newMessages[newMessages.length - 1].content = assistantMessage
                  return newMessages
                })
              }
              if (data.done) {
                setIsStreaming(false)
              }
            } catch (e) {
              console.error('Error parsing SSE:', e)
            }
          }
        }
      }
    } catch (error) {
      console.error('Error sending message:', error)
      setIsStreaming(false)
    }
  }

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'CRITICAL': return 'bg-red-600'
      case 'HIGH': return 'bg-orange-500'
      case 'MODERATE': return 'bg-yellow-500'
      case 'LOW': return 'bg-green-500'
      default: return 'bg-gray-500'
    }
  }

  const getRiskBadgeVariant = (riskLevel: string): "default" | "destructive" | "outline" | "secondary" => {
    switch (riskLevel) {
      case 'CRITICAL': return 'destructive'
      case 'HIGH': return 'destructive'
      case 'MODERATE': return 'secondary'
      case 'LOW': return 'outline'
      default: return 'default'
    }
  }

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortColumn(column)
      setSortDirection('desc')
    }
  }

  const getFilteredAndSortedPatients = () => {
    let filtered = patients

    if (filterRisk !== 'all') {
      filtered = filtered.filter(p => p.risk_level === filterRisk)
    }

    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(p => 
        p.name.toLowerCase().includes(query) ||
        p.room.toLowerCase().includes(query) ||
        p.mrn.toLowerCase().includes(query) ||
        p.diagnosis.toLowerCase().includes(query)
      )
    }

    const sorted = [...filtered].sort((a, b) => {
      let aVal: any = a[sortColumn as keyof Patient]
      let bVal: any = b[sortColumn as keyof Patient]

      if (sortColumn === 'heart_rate') {
        aVal = a.vitals.current.heart_rate
        bVal = b.vitals.current.heart_rate
      } else if (sortColumn === 'temperature') {
        aVal = a.vitals.current.temperature
        bVal = b.vitals.current.temperature
      } else if (sortColumn === 'wbc') {
        aVal = a.labs.current.wbc
        bVal = b.labs.current.wbc
      } else if (sortColumn === 'lactate') {
        aVal = a.labs.current.lactate
        bVal = b.labs.current.lactate
      }

      if (typeof aVal === 'string') {
        return sortDirection === 'asc' 
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal)
      }
      
      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal
    })

    return sorted
  }

  const openPatientDetailsWithAGUI = async (patient: Patient) => {
    setQuickViewPatient(patient)
    setQuickViewOpen(true)
    setPatientHistory([])
    setAiInsights(null)
    setLoadingHistory(true)
    setLoadingAnalysis(true)

    try {
      if (!aguiClientRef.current) {
        aguiClientRef.current = new AGUIClient(API_URL)
        await aguiClientRef.current.createSession(patient.id)
        await aguiClientRef.current.connect()

        aguiClientRef.current.on('patient.opened', (event) => {
          console.log('Patient opened:', event.payload.patient)
        })

        aguiClientRef.current.on('ui.chart.update', (event) => {
          if (event.payload.history) {
            setPatientHistory(event.payload.history)
            setLoadingHistory(false)
          }
        })

        aguiClientRef.current.on('agent.response.delta', (event) => {
          if (event.payload.type === 'analysis') {
            console.log('AG-UI analysis delta:', event.payload.content)
          }
        })

        aguiClientRef.current.on('agent.response.done', (event) => {
          if (event.payload.type === 'analysis') {
            setLoadingAnalysis(false)
          }
        })

        aguiClientRef.current.on('error', (event) => {
          console.error('AG-UI error:', event.payload)
          setLoadingHistory(false)
          setLoadingAnalysis(false)
        })
      }

      aguiClientRef.current.send('patient.open', { patientId: patient.id })
      aguiClientRef.current.send('analysis.request', { patientId: patient.id })
    } catch (error) {
      console.error('Error with AG-UI:', error)
      setLoadingHistory(false)
      setLoadingAnalysis(false)
    }
  }

  const openPatientDetails = async (patient: Patient) => {
    if (USE_AGUI) {
      return openPatientDetailsWithAGUI(patient)
    }

    setQuickViewPatient(patient)
    setQuickViewOpen(true)
    setPatientHistory([])
    setAiInsights(null)
    setHorizonForecast(null)
    setNextBestAction(null)
    setSepsisBundle(null)
    setEarlyWarning(null)
    setWhatIfPrediction(null)
    setMonteCarloPathways(null)
    setSelectedPathway(0)
    setLoadingHistory(true)
    setLoadingAnalysis(true)
    setLoadingGameChangers(true)
    setLoadingMonteCarlo(true)

    try {
      const historyResponse = await fetch(`${API_URL}/api/patients/${patient.id}/history`, {
        headers: getAuthHeaders()
      })
      const historyData = await historyResponse.json()
      setPatientHistory(historyData.history)
      setLoadingHistory(false)
    } catch (error) {
      console.error('Error fetching patient history:', error)
      setLoadingHistory(false)
    }

    try {
      const insightsResponse = await fetch(`${API_URL}/api/patients/${patient.id}/ai-insights`, {
        headers: getAuthHeaders()
      })
      const insightsData = await insightsResponse.json()
      setAiInsights(insightsData)
      setLoadingAnalysis(false)
    } catch (error) {
      console.error('Error fetching AI insights:', error)
      setLoadingAnalysis(false)
    }

    try {
      const [forecastRes, actionRes, bundleRes, earlyWarningRes] = await Promise.all([
        fetch(`${API_URL}/api/patients/${patient.id}/horizon-forecast`, { headers: getAuthHeaders() }),
        fetch(`${API_URL}/api/patients/${patient.id}/next-best-action`, { headers: getAuthHeaders() }),
        fetch(`${API_URL}/api/patients/${patient.id}/sepsis-bundle`, { headers: getAuthHeaders() }),
        fetch(`${API_URL}/api/patients/${patient.id}/early-warning`, { headers: getAuthHeaders() })
      ])
      
      const [forecastData, actionData, bundleData, earlyWarningData] = await Promise.all([
        forecastRes.json(),
        actionRes.json(),
        bundleRes.json(),
        earlyWarningRes.json()
      ])
      
      setHorizonForecast(forecastData)
      setNextBestAction(actionData)
      setSepsisBundle(bundleData)
      setEarlyWarning(earlyWarningData)
      setLoadingGameChangers(false)
    } catch (error) {
      console.error('Error fetching game-changing features:', error)
      setLoadingGameChangers(false)
    }

    try {
      const monteCarloRes = await fetch(`${API_URL}/api/patients/${patient.id}/what-if/monte-carlo`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ samples: 100 })
      })
      const monteCarloData = await monteCarloRes.json()
      setMonteCarloPathways(monteCarloData)
      if (monteCarloData.top_3_pathways && monteCarloData.top_3_pathways.length > 0) {
        const topPathway = monteCarloData.top_3_pathways[0]
        const abxCoverage = (topPathway.treatment_details?.antibiotics?.coverage || '').toLowerCase()
        const vasopressorType = (topPathway.treatment_details?.vasopressor?.type || '').toLowerCase()
        setWhatIfIntervention({
          fluids_ml: topPathway.treatment_details?.fluids?.volume_ml || 0,
          oxygen_increase: 0,
          antibiotics_given: abxCoverage !== 'none' && abxCoverage !== '',
          vasopressors_started: vasopressorType !== 'none' && vasopressorType !== ''
        })
      }
      setLoadingMonteCarlo(false)
    } catch (error) {
      console.error('Error fetching Monte Carlo pathways:', error)
      setLoadingMonteCarlo(false)
    }
  }

  const highRiskPatients = patients.filter(p => p.risk_level === 'CRITICAL' || p.risk_level === 'HIGH')
  const moderateRiskPatients = patients.filter(p => p.risk_level === 'MODERATE')
  const lowRiskPatients = patients.filter(p => p.risk_level === 'LOW')

  return (
    <div className="min-h-screen bg-dark text-white">
      <header className="bg-teams-purple shadow-lg border-b border-gray-700">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Activity className="w-8 h-8 text-white" />
              <div>
                <h1 className="text-2xl font-bold text-white">Sepsis Prevention Copilot</h1>
                <p className="text-gray-300 text-sm">AdventHealth Clinical AI Assistant</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-right">
                <p className="text-sm font-medium text-white">3 East Medical-Surgical</p>
                <p className="text-xs text-gray-300">Real-time Monitoring Active</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="bg-dark-card border-b border-gray-700">
        <div className="container mx-auto px-6">
          <div className="flex space-x-1">
            <button
              onClick={() => setCurrentView('dashboard')}
              className={`px-6 py-3 font-medium transition-colors ${
                currentView === 'dashboard'
                  ? 'text-teams-purple border-b-2 border-teams-purple'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <Users className="w-4 h-4 inline mr-2" />
              Dashboard
            </button>
            <button
              onClick={() => setCurrentView('table')}
              className={`px-6 py-3 font-medium transition-colors ${
                currentView === 'table'
                  ? 'text-teams-purple border-b-2 border-teams-purple'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <TableIcon className="w-4 h-4 inline mr-2" />
              Table
            </button>
            <button
              onClick={() => setCurrentView('chat')}
              className={`px-6 py-3 font-medium transition-colors ${
                currentView === 'chat'
                  ? 'text-teams-purple border-b-2 border-teams-purple'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <MessageSquare className="w-4 h-4 inline mr-2" />
              Chat
            </button>
            <button
              onClick={() => setCurrentView('rl-analytics')}
              className={`px-6 py-3 font-medium transition-colors ${
                currentView === 'rl-analytics'
                  ? 'text-teams-purple border-b-2 border-teams-purple'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <BarChart3 className="w-4 h-4 inline mr-2" />
              RL Analytics
            </button>
            <button
              onClick={() => setCurrentView('report')}
              className={`px-6 py-3 font-medium transition-colors ${
                currentView === 'report'
                  ? 'text-teams-purple border-b-2 border-teams-purple'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <TrendingUp className="w-4 h-4 inline mr-2" />
              Report
            </button>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-6 py-6">
        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-3">
            <Card className="mb-6 bg-dark-card border-gray-700">
              <CardHeader>
                <CardTitle className="text-white">Unit Overview</CardTitle>
                <CardDescription className="text-gray-400">Patient Risk Distribution</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 bg-red-900/20 rounded-lg border border-red-800">
                    <span className="text-sm font-medium text-white">High Risk</span>
                    <span className="text-xl font-bold text-red-400">{highRiskPatients.length}</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-yellow-900/20 rounded-lg border border-yellow-800">
                    <span className="text-sm font-medium text-white">Moderate</span>
                    <span className="text-xl font-bold text-yellow-400">{moderateRiskPatients.length}</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-green-900/20 rounded-lg border border-green-800">
                    <span className="text-sm font-medium text-white">Low Risk</span>
                    <span className="text-xl font-bold text-green-400">{lowRiskPatients.length}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-dark-card border-gray-700">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2 text-white">
                  <AlertTriangle className="w-5 h-5 text-orange-500" />
                  <span>High Risk Alerts</span>
                </CardTitle>
                <CardDescription className="text-gray-400">{highRiskPatients.length} patients need attention</CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-96">
                  <div className="space-y-3">
                    {highRiskPatients.map(patient => (
                      <div
                        key={patient.id}
                        onClick={() => openPatientDetails(patient)}
                        className="p-3 bg-dark-hover border border-orange-800 rounded-lg cursor-pointer hover:border-orange-600 transition-colors"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <p className="font-semibold text-sm text-white">{patient.name}</p>
                          <Badge variant={getRiskBadgeVariant(patient.risk_level)} className="bg-red-600 text-white">
                            {patient.risk_score}
                          </Badge>
                        </div>
                        <p className="text-xs text-gray-400">{patient.room} • {patient.mrn}</p>
                        <p className="text-xs text-gray-500 mt-1">{patient.diagnosis}</p>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </div>

          <div className="col-span-9">
            {currentView === 'dashboard' && (
              <Card className="bg-dark-card border-gray-700">
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2 text-white">
                    <Users className="w-5 h-5" />
                    <span>Patient Dashboard</span>
                  </CardTitle>
                  <CardDescription className="text-gray-400">All patients on 3 East unit ({patients.length} total)</CardDescription>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-[600px]">
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-2">
                      {patients.map(patient => (
                        <div
                          key={patient.id}
                          onClick={() => openPatientDetails(patient)}
                          className="p-2 bg-dark-hover border border-gray-700 rounded cursor-pointer hover:border-teams-purple transition-all relative group"
                        >
                          <div className="flex items-start justify-between mb-1.5">
                            <div className="flex-1 min-w-0">
                              <h3 className="font-semibold text-sm text-white truncate">{patient.name}</h3>
                              <p className="text-xs text-gray-400 truncate">{patient.room}</p>
                            </div>
                            <div className={`w-10 h-10 rounded-full ${getRiskColor(patient.risk_level)} flex items-center justify-center text-white text-xs font-bold flex-shrink-0 ml-1`}>
                              {patient.risk_score}
                            </div>
                          </div>
                          
                          <div className="grid grid-cols-2 gap-1 mb-1.5">
                            <div className="bg-dark p-1 rounded border border-gray-700">
                              <p className="text-xs text-gray-500">HR</p>
                              <p className="text-xs font-semibold text-white">{patient.vitals.current.heart_rate}</p>
                            </div>
                            <div className="bg-dark p-1 rounded border border-gray-700">
                              <p className="text-xs text-gray-500">Temp</p>
                              <p className="text-xs font-semibold text-white">{patient.vitals.current.temperature}°</p>
                            </div>
                          </div>
                          
                          <div className="flex items-center justify-between">
                            <Badge variant="outline" className="border-gray-600 text-gray-300 text-xs">SIRS: {patient.sirs_criteria}/4</Badge>
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              className="h-6 px-2 text-xs text-teams-purple hover:text-white opacity-0 group-hover:opacity-100 transition-opacity"
                              onClick={(e) => {
                                e.stopPropagation()
                                openPatientDetails(patient)
                              }}
                            >
                              Details →
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </CardContent>
              </Card>
            )}

            {currentView === 'table' && (
              <Card className="bg-dark-card border-gray-700">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-white">Patient Table</CardTitle>
                      <CardDescription className="text-gray-400">Sortable and filterable patient data</CardDescription>
                    </div>
                    <div className="flex items-center space-x-3">
                      <div className="relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500" />
                        <Input
                          type="text"
                          placeholder="Search patients..."
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          className="pl-10 bg-dark border-gray-600 text-white placeholder-gray-500"
                        />
                      </div>
                      <select
                        value={filterRisk}
                        onChange={(e) => setFilterRisk(e.target.value)}
                        className="px-3 py-2 bg-dark border border-gray-600 rounded-md text-white"
                      >
                        <option value="all">All Risk Levels</option>
                        <option value="CRITICAL">Critical</option>
                        <option value="HIGH">High</option>
                        <option value="MODERATE">Moderate</option>
                        <option value="LOW">Low</option>
                      </select>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-gray-700">
                          <th className="text-left p-3 text-gray-400 font-medium cursor-pointer hover:text-white" onClick={() => handleSort('name')}>
                            Name {sortColumn === 'name' && (sortDirection === 'asc' ? '↑' : '↓')}
                          </th>
                          <th className="text-left p-3 text-gray-400 font-medium cursor-pointer hover:text-white" onClick={() => handleSort('room')}>
                            Room {sortColumn === 'room' && (sortDirection === 'asc' ? '↑' : '↓')}
                          </th>
                          <th className="text-left p-3 text-gray-400 font-medium">Age/Gender</th>
                          <th className="text-left p-3 text-gray-400 font-medium cursor-pointer hover:text-white" onClick={() => handleSort('risk_score')}>
                            Risk {sortColumn === 'risk_score' && (sortDirection === 'asc' ? '↑' : '↓')}
                          </th>
                          <th className="text-left p-3 text-gray-400 font-medium cursor-pointer hover:text-white" onClick={() => handleSort('sirs_criteria')}>
                            SIRS {sortColumn === 'sirs_criteria' && (sortDirection === 'asc' ? '↑' : '↓')}
                          </th>
                          <th className="text-left p-3 text-gray-400 font-medium">Diagnosis</th>
                          <th className="text-left p-3 text-gray-400 font-medium cursor-pointer hover:text-white" onClick={() => handleSort('heart_rate')}>
                            HR {sortColumn === 'heart_rate' && (sortDirection === 'asc' ? '↑' : '↓')}
                          </th>
                          <th className="text-left p-3 text-gray-400 font-medium cursor-pointer hover:text-white" onClick={() => handleSort('temperature')}>
                            Temp {sortColumn === 'temperature' && (sortDirection === 'asc' ? '↑' : '↓')}
                          </th>
                          <th className="text-left p-3 text-gray-400 font-medium cursor-pointer hover:text-white" onClick={() => handleSort('wbc')}>
                            WBC {sortColumn === 'wbc' && (sortDirection === 'asc' ? '↑' : '↓')}
                          </th>
                          <th className="text-left p-3 text-gray-400 font-medium cursor-pointer hover:text-white" onClick={() => handleSort('lactate')}>
                            Lactate {sortColumn === 'lactate' && (sortDirection === 'asc' ? '↑' : '↓')}
                          </th>
                          <th className="text-left p-3 text-gray-400 font-medium">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {getFilteredAndSortedPatients().map(patient => (
                          <tr key={patient.id} className="border-b border-gray-800 hover:bg-dark-hover transition-colors">
                            <td className="p-3 text-white font-medium">{patient.name}</td>
                            <td className="p-3 text-gray-300">{patient.room}</td>
                            <td className="p-3 text-gray-300">{patient.age}y {patient.gender}</td>
                            <td className="p-3">
                              <Badge variant={getRiskBadgeVariant(patient.risk_level)} className={`${getRiskColor(patient.risk_level)} text-white`}>
                                {patient.risk_score}
                              </Badge>
                            </td>
                            <td className="p-3 text-gray-300">{patient.sirs_criteria}/4</td>
                            <td className="p-3 text-gray-300 max-w-xs truncate">{patient.diagnosis}</td>
                            <td className="p-3 text-gray-300">{patient.vitals.current.heart_rate}</td>
                            <td className="p-3 text-gray-300">{patient.vitals.current.temperature}°C</td>
                            <td className="p-3 text-gray-300">{patient.labs.current.wbc}</td>
                            <td className="p-3 text-gray-300">{patient.labs.current.lactate}</td>
                            <td className="p-3">
                              <Button
                                size="sm"
                                onClick={() => openPatientDetails(patient)}
                                className="bg-teams-purple hover:bg-purple-700 text-white"
                              >
                                Details
                              </Button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            )}

            {currentView === 'chat' && (
              <div className="space-y-4">
                {selectedPatient && (
                  <Card className="bg-dark-card border-gray-700">
                    <CardContent className="pt-6">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                          <div className={`w-16 h-16 rounded-full ${getRiskColor(selectedPatient.risk_level)} flex items-center justify-center text-white text-2xl font-bold`}>
                            {selectedPatient.risk_score}
                          </div>
                          <div>
                            <h2 className="text-2xl font-bold text-white">{selectedPatient.name}</h2>
                            <p className="text-gray-400">{selectedPatient.mrn} • {selectedPatient.room} • {selectedPatient.age}y • Admitted {selectedPatient.admission_date}</p>
                          </div>
                        </div>
                        <Button
                          variant="outline"
                          onClick={() => setSelectedPatient(null)}
                          className="border-gray-600 text-gray-300 hover:bg-dark-hover"
                        >
                          Clear
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )}

                <Card className="bg-dark-card border-gray-700">
                  <CardHeader>
                    <CardTitle className="text-white">AI Clinical Assistant</CardTitle>
                    <CardDescription className="text-gray-400">
                      {selectedPatient ? `Discussing ${selectedPatient.name}` : 'Select a patient to start chatting'}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ScrollArea className="h-96 mb-4 p-4 bg-dark rounded-lg border border-gray-700">
                      <div className="space-y-4">
                        {chatMessages.length === 0 && (
                          <div className="text-center text-gray-500 py-8">
                            <MessageSquare className="w-12 h-12 mx-auto mb-3 text-gray-600" />
                            <p className="text-sm">Start a conversation with the AI assistant</p>
                            <p className="text-xs mt-2">Try: "Assess sepsis risk for this patient"</p>
                          </div>
                        )}
                        {chatMessages.map((msg, idx) => (
                          <div
                            key={idx}
                            className={`p-3 rounded-lg ${
                              msg.role === 'user'
                                ? 'bg-teams-purple ml-8 text-white'
                                : 'bg-dark-hover mr-8 text-gray-200'
                            }`}
                          >
                            <p className="text-xs font-semibold mb-1 text-gray-400">
                              {msg.role === 'user' ? 'You' : 'AI Assistant'}
                            </p>
                            <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                          </div>
                        ))}
                        {isStreaming && (
                          <div className="flex items-center space-x-2 text-gray-500">
                            <div className="animate-pulse">●</div>
                            <p className="text-sm">AI is thinking...</p>
                          </div>
                        )}
                        <div ref={chatEndRef} />
                      </div>
                    </ScrollArea>

                    <div className="flex items-center space-x-3">
                      <Button
                        onClick={toggleVoiceRecognition}
                        className={`${isListening ? 'bg-red-600 hover:bg-red-700' : 'bg-teams-purple hover:bg-purple-700'} text-white`}
                      >
                        {isListening ? (
                          <>
                            <MicOff className="w-5 h-5 mr-2" />
                            Stop
                          </>
                        ) : (
                          <>
                            <Mic className="w-5 h-5 mr-2" />
                            Voice
                          </>
                        )}
                      </Button>
                      <Input
                        type="text"
                        placeholder="Type a message..."
                        value={transcript}
                        onChange={(e) => setTranscript(e.target.value)}
                        onKeyPress={(e) => {
                          if (e.key === 'Enter' && !isStreaming) {
                            handleSendMessage(transcript)
                          }
                        }}
                        className="flex-1 bg-dark border-gray-600 text-white placeholder-gray-500"
                        disabled={isStreaming}
                      />
                      <Button
                        onClick={() => handleSendMessage(transcript)}
                        disabled={isStreaming || !transcript.trim()}
                        className="bg-teams-purple hover:bg-purple-700 text-white"
                      >
                        Send
                      </Button>
                    </div>
                  </CardContent>
                </Card>

                {selectedPatient && (
                  <Card className="bg-dark-card border-gray-700">
                    <CardHeader>
                      <CardTitle className="text-white">Patient Details</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <Tabs defaultValue="vitals">
                        <TabsList className="grid w-full grid-cols-4 bg-dark">
                          <TabsTrigger value="vitals" className="data-[state=active]:bg-teams-purple data-[state=active]:text-white">Vitals</TabsTrigger>
                          <TabsTrigger value="labs" className="data-[state=active]:bg-teams-purple data-[state=active]:text-white">Labs</TabsTrigger>
                          <TabsTrigger value="devices" className="data-[state=active]:bg-teams-purple data-[state=active]:text-white">Devices</TabsTrigger>
                          <TabsTrigger value="notes" className="data-[state=active]:bg-teams-purple data-[state=active]:text-white">Notes</TabsTrigger>
                        </TabsList>
                        
                        <TabsContent value="vitals" className="space-y-4">
                          <div className="grid grid-cols-5 gap-4">
                            <Card className="bg-dark border-gray-700">
                              <CardHeader className="pb-2">
                                <CardTitle className="text-sm text-gray-400">Heart Rate</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <p className="text-2xl font-bold text-white">{selectedPatient.vitals.current.heart_rate}</p>
                                <p className="text-xs text-gray-500">
                                  Previous: {selectedPatient.vitals.previous.heart_rate}
                                </p>
                              </CardContent>
                            </Card>
                            
                            <Card className="bg-dark border-gray-700">
                              <CardHeader className="pb-2">
                                <CardTitle className="text-sm text-gray-400">Resp Rate</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <p className="text-2xl font-bold text-white">{selectedPatient.vitals.current.respiratory_rate}</p>
                                <p className="text-xs text-gray-500">
                                  Previous: {selectedPatient.vitals.previous.respiratory_rate}
                                </p>
                              </CardContent>
                            </Card>
                            
                            <Card className="bg-dark border-gray-700">
                              <CardHeader className="pb-2">
                                <CardTitle className="text-sm text-gray-400">Temperature</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <p className="text-2xl font-bold text-white">{selectedPatient.vitals.current.temperature}°C</p>
                                <p className="text-xs text-gray-500">
                                  Previous: {selectedPatient.vitals.previous.temperature}°C
                                </p>
                              </CardContent>
                            </Card>
                            
                            <Card className="bg-dark border-gray-700">
                              <CardHeader className="pb-2">
                                <CardTitle className="text-sm text-gray-400">BP</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <p className="text-2xl font-bold text-white">{selectedPatient.vitals.current.blood_pressure}</p>
                                <p className="text-xs text-gray-500">
                                  Previous: {selectedPatient.vitals.previous.blood_pressure}
                                </p>
                              </CardContent>
                            </Card>
                            
                            <Card className="bg-dark border-gray-700">
                              <CardHeader className="pb-2">
                                <CardTitle className="text-sm text-gray-400">SpO2</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <p className="text-2xl font-bold text-white">{selectedPatient.vitals.current.spo2}%</p>
                                <p className="text-xs text-gray-500">
                                  Previous: {selectedPatient.vitals.previous.spo2}%
                                </p>
                              </CardContent>
                            </Card>
                          </div>
                        </TabsContent>
                        
                        <TabsContent value="labs" className="space-y-4">
                          <div className="grid grid-cols-4 gap-4">
                            <Card className="bg-dark border-gray-700">
                              <CardHeader className="pb-2">
                                <CardTitle className="text-sm text-gray-400">WBC</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <p className="text-2xl font-bold text-white">{selectedPatient.labs.current.wbc}</p>
                                <p className="text-xs text-gray-500">
                                  Previous: {selectedPatient.labs.previous.wbc}
                                </p>
                              </CardContent>
                            </Card>
                            
                            <Card className="bg-dark border-gray-700">
                              <CardHeader className="pb-2">
                                <CardTitle className="text-sm text-gray-400">Lactate</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <p className="text-2xl font-bold text-white">{selectedPatient.labs.current.lactate}</p>
                                <p className="text-xs text-gray-500">
                                  Previous: {selectedPatient.labs.previous.lactate}
                                </p>
                              </CardContent>
                            </Card>
                            
                            <Card className="bg-dark border-gray-700">
                              <CardHeader className="pb-2">
                                <CardTitle className="text-sm text-gray-400">Creatinine</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <p className="text-2xl font-bold text-white">{selectedPatient.labs.current.creatinine}</p>
                                <p className="text-xs text-gray-500">
                                  Previous: {selectedPatient.labs.previous.creatinine}
                                </p>
                              </CardContent>
                            </Card>
                            
                            <Card className="bg-dark border-gray-700">
                              <CardHeader className="pb-2">
                                <CardTitle className="text-sm text-gray-400">Bilirubin</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <p className="text-2xl font-bold text-white">{selectedPatient.labs.current.bilirubin}</p>
                                <p className="text-xs text-gray-500">
                                  Previous: {selectedPatient.labs.previous.bilirubin}
                                </p>
                              </CardContent>
                            </Card>
                          </div>
                        </TabsContent>
                        
                        <TabsContent value="devices">
                          <div className="space-y-3">
                            {selectedPatient.devices.map((device, idx) => (
                              <Card key={idx} className="bg-dark border-gray-700">
                                <CardContent className="pt-6">
                                  <div className="flex items-center justify-between">
                                    <div>
                                      <p className="font-semibold text-white">{device.type}</p>
                                      <p className="text-sm text-gray-400">Day {device.days}</p>
                                    </div>
                                    {device.days >= 3 && device.type.includes('catheter') && (
                                      <Badge variant="destructive" className="bg-red-600 text-white">Consider Removal</Badge>
                                    )}
                                  </div>
                                </CardContent>
                              </Card>
                            ))}
                          </div>
                        </TabsContent>
                        
                        <TabsContent value="notes">
                          <div className="space-y-3">
                            {selectedPatient.notes.map((note, idx) => (
                              <Card key={idx} className="bg-dark border-gray-700">
                                <CardContent className="pt-6">
                                  <p className="text-sm font-semibold text-gray-400 mb-1">{note.time}</p>
                                  <p className="text-sm text-gray-200">{note.note}</p>
                                </CardContent>
                              </Card>
                            ))}
                          </div>
                        </TabsContent>
                      </Tabs>
                    </CardContent>
                  </Card>
                )}
              </div>
            )}

            {currentView === 'rl-analytics' && (
              <div className="space-y-6">
                <Card className="bg-dark-card border-gray-700">
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2 text-white">
                      <BarChart3 className="w-5 h-5 text-teams-purple" />
                      <span>Reinforcement Learning Analytics</span>
                    </CardTitle>
                    <CardDescription className="text-gray-400">
                      How RL is improving sepsis treatment pathway modeling across 500+ scenarios
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {loadingRlResults ? (
                      <div className="space-y-4">
                        <Skeleton className="h-64 w-full bg-gray-700" />
                        <Skeleton className="h-64 w-full bg-gray-700" />
                      </div>
                    ) : rlResults ? (
                      <div className="space-y-6">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <Card className="bg-dark border-gray-700">
                            <CardContent className="pt-6">
                              <div className="text-center">
                                <p className="text-xs text-gray-400 mb-2">Total Scenarios</p>
                                <p className="text-3xl font-bold text-teams-purple">{rlResults.insights?.total_scenarios || 500}</p>
                              </div>
                            </CardContent>
                          </Card>
                          <Card className="bg-dark border-gray-700">
                            <CardContent className="pt-6">
                              <div className="text-center">
                                <p className="text-xs text-gray-400 mb-2">Batches Evaluated</p>
                                <p className="text-3xl font-bold text-teams-purple">{rlResults.learning_curves?.length || 5}</p>
                              </div>
                            </CardContent>
                          </Card>
                          <Card className="bg-dark border-gray-700">
                            <CardContent className="pt-6">
                              <div className="text-center">
                                <p className="text-xs text-gray-400 mb-2">Simulations per Pathway</p>
                                <p className="text-3xl font-bold text-teams-purple">100</p>
                              </div>
                            </CardContent>
                          </Card>
                        </div>

                        {rlResults.learning_curves && rlResults.learning_curves.length > 0 && (
                          <>
                            <Card className="bg-dark border-gray-700">
                              <CardHeader>
                                <CardTitle className="text-white text-lg">Learning Curves: Win Rate Over Time</CardTitle>
                                <CardDescription className="text-gray-400">
                                  RL policy performance vs baseline across 5 sequential batches
                                </CardDescription>
                              </CardHeader>
                              <CardContent>
                                <ResponsiveContainer width="100%" height={300}>
                                  <LineChart data={rlResults.learning_curves}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                    <XAxis 
                                      dataKey="batch_id" 
                                      stroke="#9CA3AF"
                                      label={{ value: 'Batch', position: 'insideBottom', offset: -5, fill: '#9CA3AF' }}
                                    />
                                    <YAxis 
                                      stroke="#9CA3AF"
                                      label={{ value: 'Win Rate (%)', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }}
                                      domain={[0, 100]}
                                    />
                                    <Tooltip 
                                      contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }}
                                      labelStyle={{ color: '#F3F4F6' }}
                                    />
                                    <Legend />
                                    <Line 
                                      type="monotone" 
                                      dataKey="rl_win_rate" 
                                      stroke="#8B5CF6" 
                                      strokeWidth={3}
                                      name="RL Policy"
                                      dot={{ fill: '#8B5CF6', r: 5 }}
                                    />
                                    <Line 
                                      type="monotone" 
                                      dataKey="baseline_win_rate" 
                                      stroke="#10B981" 
                                      strokeWidth={3}
                                      name="Baseline"
                                      dot={{ fill: '#10B981', r: 5 }}
                                    />
                                  </LineChart>
                                </ResponsiveContainer>
                              </CardContent>
                            </Card>

                            <Card className="bg-dark border-gray-700">
                              <CardHeader>
                                <CardTitle className="text-white text-lg">Expected Utility Comparison</CardTitle>
                                <CardDescription className="text-gray-400">
                                  Mean utility scores across batches (higher is better)
                                </CardDescription>
                              </CardHeader>
                              <CardContent>
                                <ResponsiveContainer width="100%" height={300}>
                                  <LineChart data={rlResults.learning_curves}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                    <XAxis 
                                      dataKey="batch_id" 
                                      stroke="#9CA3AF"
                                      label={{ value: 'Batch', position: 'insideBottom', offset: -5, fill: '#9CA3AF' }}
                                    />
                                    <YAxis 
                                      stroke="#9CA3AF"
                                      label={{ value: 'Mean Utility', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }}
                                    />
                                    <Tooltip 
                                      contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }}
                                      labelStyle={{ color: '#F3F4F6' }}
                                    />
                                    <Legend />
                                    <Line 
                                      type="monotone" 
                                      dataKey="rl_mean_utility" 
                                      stroke="#8B5CF6" 
                                      strokeWidth={3}
                                      name="RL Policy"
                                      dot={{ fill: '#8B5CF6', r: 5 }}
                                    />
                                    <Line 
                                      type="monotone" 
                                      dataKey="baseline_mean_utility" 
                                      stroke="#10B981" 
                                      strokeWidth={3}
                                      name="Baseline"
                                      dot={{ fill: '#10B981', r: 5 }}
                                    />
                                  </LineChart>
                                </ResponsiveContainer>
                              </CardContent>
                            </Card>

                            <Card className="bg-dark border-gray-700">
                              <CardHeader>
                                <CardTitle className="text-white text-lg">Regret Over Time</CardTitle>
                                <CardDescription className="text-gray-400">
                                  Distance from optimal choice (lower is better)
                                </CardDescription>
                              </CardHeader>
                              <CardContent>
                                <ResponsiveContainer width="100%" height={300}>
                                  <LineChart data={rlResults.learning_curves}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                    <XAxis 
                                      dataKey="batch_id" 
                                      stroke="#9CA3AF"
                                      label={{ value: 'Batch', position: 'insideBottom', offset: -5, fill: '#9CA3AF' }}
                                    />
                                    <YAxis 
                                      stroke="#9CA3AF"
                                      label={{ value: 'Mean Regret', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }}
                                    />
                                    <Tooltip 
                                      contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }}
                                      labelStyle={{ color: '#F3F4F6' }}
                                    />
                                    <Legend />
                                    <Line 
                                      type="monotone" 
                                      dataKey="rl_mean_regret" 
                                      stroke="#EF4444" 
                                      strokeWidth={3}
                                      name="RL Regret"
                                      dot={{ fill: '#EF4444', r: 5 }}
                                    />
                                    <Line 
                                      type="monotone" 
                                      dataKey="baseline_mean_regret" 
                                      stroke="#F59E0B" 
                                      strokeWidth={3}
                                      name="Baseline Regret"
                                      dot={{ fill: '#F59E0B', r: 5 }}
                                    />
                                  </LineChart>
                                </ResponsiveContainer>
                              </CardContent>
                            </Card>
                          </>
                        )}

                        {rlResults.insights && (
                          <>
                            <Card className="bg-dark border-gray-700">
                              <CardHeader>
                                <CardTitle className="text-white text-lg">Stratified Performance by Risk Level</CardTitle>
                                <CardDescription className="text-gray-400">
                                  RL win rate across different patient risk categories
                                </CardDescription>
                              </CardHeader>
                              <CardContent>
                                {rlResults.insights.stratified_by_risk && (
                                  <ResponsiveContainer width="100%" height={300}>
                                    <BarChart data={Object.entries(rlResults.insights.stratified_by_risk).map(([risk, data]: [string, any]) => ({
                                      risk_level: risk,
                                      win_rate: data.rl_win_rate * 100,
                                      scenarios: data.count
                                    }))}>
                                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                      <XAxis 
                                        dataKey="risk_level" 
                                        stroke="#9CA3AF"
                                      />
                                      <YAxis 
                                        stroke="#9CA3AF"
                                        label={{ value: 'Win Rate (%)', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }}
                                        domain={[0, 100]}
                                      />
                                      <Tooltip 
                                        contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }}
                                        labelStyle={{ color: '#F3F4F6' }}
                                      />
                                      <Bar dataKey="win_rate" fill="#8B5CF6" />
                                    </BarChart>
                                  </ResponsiveContainer>
                                )}
                              </CardContent>
                            </Card>

                            {rlResults.insights.feature_importance && rlResults.insights.feature_importance.length > 0 && (
                              <Card className="bg-dark border-gray-700">
                                <CardHeader>
                                  <CardTitle className="text-white text-lg">Top 10 Feature Importance</CardTitle>
                                  <CardDescription className="text-gray-400">
                                    Which patient characteristics predict treatment pathway success
                                  </CardDescription>
                                </CardHeader>
                                <CardContent>
                                  <ResponsiveContainer width="100%" height={400}>
                                    <BarChart 
                                      data={rlResults.insights.feature_importance.slice(0, 10)}
                                      layout="vertical"
                                      margin={{ left: 120 }}
                                    >
                                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                      <XAxis 
                                        type="number"
                                        stroke="#9CA3AF"
                                        label={{ value: 'Importance Score', position: 'insideBottom', offset: -5, fill: '#9CA3AF' }}
                                      />
                                      <YAxis 
                                        type="category"
                                        dataKey="feature" 
                                        stroke="#9CA3AF"
                                        width={110}
                                      />
                                      <Tooltip 
                                        contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }}
                                        labelStyle={{ color: '#F3F4F6' }}
                                      />
                                      <Bar dataKey="importance" fill="#8B5CF6" />
                                    </BarChart>
                                  </ResponsiveContainer>
                                </CardContent>
                              </Card>
                            )}

                            {rlResults.insights.candidate_frequency && (
                              <Card className="bg-dark border-gray-700">
                                <CardHeader>
                                  <CardTitle className="text-white text-lg">Treatment Pathway Distribution</CardTitle>
                                  <CardDescription className="text-gray-400">
                                    How RL diversifies candidate selection over time
                                  </CardDescription>
                                </CardHeader>
                                <CardContent>
                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {Object.entries(rlResults.insights.candidate_frequency).map(([candidate, count]: [string, any]) => (
                                      <div key={candidate} className="p-4 bg-dark rounded-lg border border-gray-700">
                                        <div className="flex items-center justify-between mb-2">
                                          <p className="text-sm font-semibold text-white">{candidate}</p>
                                          <Badge variant="outline" className="border-teams-purple text-teams-purple">
                                            {count} selections
                                          </Badge>
                                        </div>
                                        <div className="w-full bg-gray-700 rounded-full h-2">
                                          <div 
                                            className="bg-teams-purple h-2 rounded-full" 
                                            style={{ width: `${(count / rlResults.insights.total_scenarios) * 100}%` }}
                                          />
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </CardContent>
                              </Card>
                            )}

                            <Card className="bg-dark border-gray-700">
                              <CardHeader>
                                <CardTitle className="text-white text-lg">Key Insights</CardTitle>
                                <CardDescription className="text-gray-400">
                                  What the RL policy learned from 500+ scenarios
                                </CardDescription>
                              </CardHeader>
                              <CardContent>
                                <div className="space-y-3">
                                  <div className="p-4 bg-blue-950/30 border border-blue-600/40 rounded-lg">
                                    <div className="flex items-start space-x-3">
                                      <Brain className="w-5 h-5 text-blue-400 mt-0.5" />
                                      <div>
                                        <p className="text-sm font-semibold text-white mb-1">Patient-Specific Selection</p>
                                        <p className="text-xs text-gray-300">
                                          RL learns to personalize treatment pathways based on patient risk level, infection source, and physiologic state. 
                                          Strong performance on LOW risk patients (83-94% win rate) demonstrates context-aware decision making.
                                        </p>
                                      </div>
                                    </div>
                                  </div>
                                  <div className="p-4 bg-purple-950/30 border border-purple-600/40 rounded-lg">
                                    <div className="flex items-start space-x-3">
                                      <TrendingUp className="w-5 h-5 text-purple-400 mt-0.5" />
                                      <div>
                                        <p className="text-sm font-semibold text-white mb-1">Exploration & Diversification</p>
                                        <p className="text-xs text-gray-300">
                                          Policy explores diverse pathways beyond rule-based defaults, learning when to deviate from 
                                          standard protocols based on patient-specific features.
                                        </p>
                                      </div>
                                    </div>
                                  </div>
                                  <div className="p-4 bg-green-950/30 border border-green-600/40 rounded-lg">
                                    <div className="flex items-start space-x-3">
                                      <Beaker className="w-5 h-5 text-green-400 mt-0.5" />
                                      <div>
                                        <p className="text-sm font-semibold text-white mb-1">Feature Importance</p>
                                        <p className="text-xs text-gray-300">
                                          MAP, SpO2, and antibiotic susceptibility are the most predictive features for pathway success, 
                                          providing explainable insights for clinical decision support.
                                        </p>
                                      </div>
                                    </div>
                                  </div>
                                </div>
                              </CardContent>
                            </Card>
                          </>
                        )}
                      </div>
                    ) : (
                      <div className="text-center py-12">
                        <BarChart3 className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                        <p className="text-gray-400 mb-2">No RL results available</p>
                        <p className="text-sm text-gray-500">Run batch evaluation to generate learning curves and insights</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            )}

            {currentView === 'report' && (
              <div className="space-y-6">
                <Card className="bg-dark-card border-gray-700">
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2 text-white">
                      <TrendingUp className="w-5 h-5 text-teams-purple" />
                      <span>AI/RL Impact Report</span>
                    </CardTitle>
                    <CardDescription className="text-gray-400">
                      Trending outcomes showing how AI and reinforcement learning are improving sepsis care
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="text-center py-12">
                      <TrendingUp className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                      <p className="text-gray-400 mb-2">Report Tab - Coming Soon</p>
                      <p className="text-sm text-gray-500">
                        This tab will show trending visualizations including:
                        <br />• Survival probability trends (with p25-p75 bands)
                        <br />• Time to stability trends (with p25-p75 bands)
                        <br />• Sepsis bundle compliance trending up
                        <br />• Early warning lead time trending up
                        <br />• Pathway adoption mix (stacked area chart)
                        <br />• Delta vs baseline comparison
                        <br />• Executive summary with key metrics
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        </div>
      </div>

      <Dialog open={quickViewOpen} onOpenChange={setQuickViewOpen}>
        <DialogContent className="max-w-none bg-dark-card border-gray-700 text-white overflow-y-auto w-[95vw] md:w-[75vw] max-w-[1600px] h-[92vh] md:h-[85vh] p-6 rounded-lg">
          {quickViewPatient && (
            <>
              <DialogHeader>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <div className={`w-14 h-14 rounded-full ${getRiskColor(quickViewPatient.risk_level)} flex items-center justify-center text-white text-xl font-bold`}>
                      {quickViewPatient.risk_score}
                    </div>
                    <div>
                      <DialogTitle className="text-white text-xl">{quickViewPatient.name}</DialogTitle>
                      <DialogDescription className="text-gray-400">
                        {quickViewPatient.mrn} • {quickViewPatient.room} • {quickViewPatient.age}y {quickViewPatient.gender}
                      </DialogDescription>
                    </div>
                  </div>
                </div>
              </DialogHeader>

              <div className="mt-6 space-y-6">
                <div>
                  <h3 className="text-sm font-semibold text-gray-400 mb-2">Current Status</h3>
                  <div className="grid grid-cols-2 gap-3">
                    <Card className="bg-dark border-gray-700">
                      <CardContent className="pt-4">
                        <p className="text-xs text-gray-500">Diagnosis</p>
                        <p className="text-sm font-semibold text-white mt-1">{quickViewPatient.diagnosis}</p>
                      </CardContent>
                    </Card>
                    <Card className="bg-dark border-gray-700">
                      <CardContent className="pt-4">
                        <p className="text-xs text-gray-500">SIRS Criteria</p>
                        <p className="text-sm font-semibold text-white mt-1">{quickViewPatient.sirs_criteria}/4</p>
                      </CardContent>
                    </Card>
                  </div>
                </div>

                <div>
                  <div className="flex items-center space-x-2 mb-3">
                    <TrendingUp className="w-5 h-5 text-teams-purple" />
                    <h3 className="text-sm font-semibold text-white">12-Hour Trends</h3>
                  </div>
                  
                  {loadingHistory ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <Skeleton className="h-40 w-full bg-gray-700" />
                      <Skeleton className="h-40 w-full bg-gray-700" />
                    </div>
                  ) : patientHistory.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-5">
                      <Card className="bg-dark border-gray-700 min-w-0">
                        <CardHeader className="py-2 px-3">
                          <CardTitle className="text-xs text-gray-400">Heart Rate & Temperature</CardTitle>
                        </CardHeader>
                        <CardContent className="px-3 pb-3">
                          <div className="h-[140px] md:h-[160px]">
                            <ResponsiveContainer width="100%" height="100%">
                              <LineChart data={patientHistory} margin={{ top: 6, right: 8, bottom: 6, left: 8 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                                <XAxis 
                                  dataKey="timestamp" 
                                  stroke="#9ca3af"
                                  tick={{ fill: '#9ca3af', fontSize: 10 }}
                                  tickFormatter={(value) => new Date(value).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                                />
                                <YAxis yAxisId="left" stroke="#9ca3af" tick={{ fill: '#9ca3af', fontSize: 10 }} />
                                <YAxis yAxisId="right" orientation="right" stroke="#9ca3af" tick={{ fill: '#9ca3af', fontSize: 10 }} />
                                <Tooltip 
                                  contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '0.375rem' }}
                                  labelStyle={{ color: '#9ca3af' }}
                                  itemStyle={{ color: '#fff' }}
                                  labelFormatter={(value) => new Date(value).toLocaleString()}
                                />
                                <Legend wrapperStyle={{ fontSize: 11 }} iconSize={8} />
                                <Line yAxisId="left" type="monotone" dataKey="heart_rate" stroke="#ef4444" name="HR (bpm)" strokeWidth={2} dot={false} />
                                <Line yAxisId="right" type="monotone" dataKey="temperature" stroke="#f59e0b" name="Temp (°C)" strokeWidth={2} dot={false} />
                              </LineChart>
                            </ResponsiveContainer>
                          </div>
                        </CardContent>
                      </Card>

                      <Card className="bg-dark border-gray-700 min-w-0">
                        <CardHeader className="py-2 px-3">
                          <CardTitle className="text-xs text-gray-400">WBC & Lactate</CardTitle>
                        </CardHeader>
                        <CardContent className="px-3 pb-3">
                          <div className="h-[140px] md:h-[160px]">
                            <ResponsiveContainer width="100%" height="100%">
                              <LineChart data={patientHistory} margin={{ top: 6, right: 8, bottom: 6, left: 8 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                                <XAxis 
                                  dataKey="timestamp" 
                                  stroke="#9ca3af"
                                  tick={{ fill: '#9ca3af', fontSize: 10 }}
                                  tickFormatter={(value) => new Date(value).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                                />
                                <YAxis yAxisId="left" stroke="#9ca3af" tick={{ fill: '#9ca3af', fontSize: 10 }} />
                                <YAxis yAxisId="right" orientation="right" stroke="#9ca3af" tick={{ fill: '#9ca3af', fontSize: 10 }} />
                                <Tooltip 
                                  contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '0.375rem' }}
                                  labelStyle={{ color: '#9ca3af' }}
                                  itemStyle={{ color: '#fff' }}
                                  labelFormatter={(value) => new Date(value).toLocaleString()}
                                />
                                <Legend wrapperStyle={{ fontSize: 11 }} iconSize={8} />
                                <Line yAxisId="left" type="monotone" dataKey="wbc" stroke="#8b5cf6" name="WBC (K/µL)" strokeWidth={2} dot={false} />
                                <Line yAxisId="right" type="monotone" dataKey="lactate" stroke="#10b981" name="Lactate (mmol/L)" strokeWidth={2} dot={false} />
                              </LineChart>
                            </ResponsiveContainer>
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">No historical data available</p>
                  )}
                </div>

                <div>
                  <div className="flex items-center space-x-2 mb-3">
                    <Brain className="w-5 h-5 text-teams-purple" />
                    <h3 className="text-sm font-semibold text-white">AI Clinical Insights</h3>
                  </div>
                  
                  {loadingAnalysis ? (
                    <div className="space-y-3">
                      <Skeleton className="h-20 w-full bg-gray-700 rounded-lg" />
                      <Skeleton className="h-20 w-full bg-gray-700 rounded-lg" />
                      <Skeleton className="h-20 w-full bg-gray-700 rounded-lg" />
                    </div>
                  ) : aiInsights?.cards && aiInsights.cards.length > 0 ? (
                    <div className="space-y-3">
                      {aiInsights.cards.map((card: any) => {
                        const variantStyles = {
                          critical: { bg: 'bg-red-950/30', border: 'border-red-600/40', header: 'text-red-300', icon: 'text-red-300' },
                          warning: { bg: 'bg-amber-950/30', border: 'border-amber-600/40', header: 'text-amber-300', icon: 'text-amber-300' },
                          info: { bg: 'bg-sky-950/40', border: 'border-sky-600/40', header: 'text-sky-300', icon: 'text-sky-300' },
                          success: { bg: 'bg-emerald-950/30', border: 'border-emerald-600/40', header: 'text-emerald-300', icon: 'text-emerald-300' },
                        }
                        
                        const variant = variantStyles[card.severity as keyof typeof variantStyles] || variantStyles.info
                        
                        const iconMap: Record<string, any> = {
                          'alert-triangle': AlertTriangle,
                          'activity': Activity,
                          'beaker': Beaker,
                          'trending-up': TrendingUp,
                          'stethoscope': Stethoscope,
                          'thermometer': Thermometer,
                          'clock': Clock,
                          'check-circle': CheckCircle2,
                        }
                        
                        const IconComponent = iconMap[card.icon] || AlertTriangle
                        
                        const timeAgo = (ts: string) => {
                          const now = new Date()
                          const then = new Date(ts)
                          const diffMs = now.getTime() - then.getTime()
                          const diffMins = Math.floor(diffMs / 60000)
                          if (diffMins < 1) return 'just now'
                          if (diffMins === 1) return '1 minute ago'
                          if (diffMins < 60) return `${diffMins} minutes ago`
                          const diffHours = Math.floor(diffMins / 60)
                          if (diffHours === 1) return '1 hour ago'
                          return `${diffHours} hours ago`
                        }
                        
                        return (
                          <div
                            key={card.id}
                            className={`rounded-lg border p-3 ${variant.bg} ${variant.border}`}
                          >
                            <div className="flex items-start space-x-3">
                              <IconComponent className={`w-5 h-5 mt-0.5 flex-shrink-0 ${variant.icon}`} />
                              <div className="flex-1 min-w-0">
                                <h4 className={`text-sm font-semibold ${variant.header} mb-1`}>
                                  {card.title}
                                </h4>
                                <p className="text-sm text-gray-200 leading-relaxed mb-2">
                                  {card.description}
                                </p>
                                <p className="text-xs text-gray-400">
                                  {card.agent} • {timeAgo(card.ts)}
                                </p>
                              </div>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">No insights available</p>
                  )}
                </div>

                {loadingGameChangers ? (
                  <div className="space-y-4">
                    <Skeleton className="h-32 w-full bg-gray-700 rounded-lg" />
                    <Skeleton className="h-32 w-full bg-gray-700 rounded-lg" />
                  </div>
                ) : (
                  <>
                    {horizonForecast && (
                      <div className="border-t border-gray-700 pt-4">
                        <div className="flex items-center space-x-2 mb-3">
                          <TrendingUp className="w-5 h-5 text-blue-400" />
                          <h3 className="text-sm font-semibold text-white">Predictive Horizon Forecast</h3>
                        </div>
                        <div className="bg-slate-900/70 border border-slate-600 rounded-lg p-4">
                          <div className="grid grid-cols-3 gap-3 mb-3">
                            {horizonForecast.forecasts.map((f: any) => (
                              <div key={f.horizon} className="text-center">
                                <div className="text-xs text-gray-400 mb-1">{f.horizon}</div>
                                <div className={`text-lg font-bold ${f.risk >= 70 ? 'text-red-400' : f.risk >= 50 ? 'text-amber-400' : 'text-green-400'}`}>
                                  {f.risk}
                                </div>
                                <div className="text-xs text-gray-500">{Math.round(f.confidence * 100)}% conf</div>
                              </div>
                            ))}
                          </div>
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-gray-400">
                              Trend: <span className={horizonForecast.trend_direction === 'rising' ? 'text-red-400' : 'text-green-400'}>
                                {horizonForecast.trend_direction}
                              </span>
                            </span>
                            {horizonForecast.time_to_breach && (
                              <span className="text-amber-400">⚠ Breach in {horizonForecast.time_to_breach}</span>
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {nextBestAction && nextBestAction.actions && nextBestAction.actions.length > 0 && (
                      <div className="border-t border-gray-700 pt-4">
                        <div className="flex items-center space-x-2 mb-3">
                          <CheckCircle2 className="w-5 h-5 text-green-400" />
                          <h3 className="text-sm font-semibold text-white">Next Best Actions</h3>
                        </div>
                        <div className="space-y-2">
                          {nextBestAction.actions.map((action: any, idx: number) => (
                            <div key={idx} className="bg-slate-900/70 border border-slate-600 rounded-lg p-3">
                              <div className="flex items-start space-x-3">
                                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                                  action.expected_benefit === 'high' ? 'bg-red-900/50 text-red-300' : 'bg-amber-900/50 text-amber-300'
                                }`}>
                                  {idx + 1}
                                </div>
                                <div className="flex-1 min-w-0">
                                  <h4 className="text-sm font-semibold text-white mb-1">{action.title}</h4>
                                  <p className="text-xs text-gray-300 mb-2">{action.rationale}</p>
                                  <div className="flex items-center space-x-3 text-xs">
                                    <span className={`px-2 py-0.5 rounded ${
                                      action.urgency === 'immediate' ? 'bg-red-900/50 text-red-300' : 'bg-amber-900/50 text-amber-300'
                                    }`}>
                                      {action.urgency}
                                    </span>
                                    <span className="text-gray-400">
                                      Confidence: {Math.round(action.confidence * 100)}%
                                    </span>
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {sepsisBundle && sepsisBundle.bundle_active && (
                      <div className="border-t border-gray-700 pt-4">
                        <div className="flex items-center space-x-2 mb-3">
                          <Clock className="w-5 h-5 text-orange-400" />
                          <h3 className="text-sm font-semibold text-white">1-Hour Sepsis Bundle</h3>
                        </div>
                        <div className="bg-slate-900/70 border border-slate-600 rounded-lg p-4">
                          <div className="flex items-center justify-between mb-4">
                            <div className="text-sm">
                              <span className="text-gray-400">Time Remaining:</span>
                              <span className={`ml-2 font-bold ${sepsisBundle.remaining_minutes < 15 ? 'text-red-400' : 'text-amber-400'}`}>
                                {Math.floor(sepsisBundle.remaining_minutes)} min
                              </span>
                            </div>
                            <div className="text-sm">
                              <span className="text-gray-400">Progress:</span>
                              <span className="ml-2 font-bold text-white">
                                {sepsisBundle.completed_count}/{sepsisBundle.total_count}
                              </span>
                            </div>
                          </div>
                          <div className="space-y-2">
                            {sepsisBundle.tasks.map((task: any) => (
                              <div key={task.id} className="flex items-center space-x-3">
                                <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                                  task.completed ? 'bg-green-900/50 border-green-600' : 
                                  task.blocked ? 'bg-gray-800 border-gray-600' : 'bg-slate-900 border-slate-600'
                                }`}>
                                  {task.completed && <CheckCircle2 className="w-4 h-4 text-green-400" />}
                                </div>
                                <div className="flex-1">
                                  <div className={`text-sm ${task.completed ? 'text-gray-400 line-through' : 'text-white'}`}>
                                    {task.title}
                                  </div>
                                  {task.blocked && task.blocker_reason && (
                                    <div className="text-xs text-amber-400 mt-1">⚠ {task.blocker_reason}</div>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                          {sepsisBundle.escalation_needed && (
                            <div className="mt-3 p-2 bg-red-900/30 border border-red-600/40 rounded text-xs text-red-300">
                              ⚠ {sepsisBundle.escalation_message}
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                    <div className="border-t border-gray-700 pt-4">
                      <div className="flex items-center space-x-2 mb-3">
                        <Beaker className="w-5 h-5 text-cyan-400" />
                        <h3 className="text-sm font-semibold text-white">What-If Simulator (Monte Carlo)</h3>
                      </div>
                      <div className="bg-slate-900/70 border border-slate-600 rounded-lg p-4">
                        {loadingMonteCarlo ? (
                          <div className="space-y-3">
                            <Skeleton className="h-16 w-full bg-gray-700 rounded-lg" />
                            <Skeleton className="h-32 w-full bg-gray-700 rounded-lg" />
                          </div>
                        ) : monteCarloPathways && monteCarloPathways.top_3_pathways ? (
                          <div className="space-y-4">
                            <div>
                              <div className="text-xs text-gray-400 mb-2">Top 3 Treatment Pathways</div>
                              <div className="grid grid-cols-3 gap-2">
                                {(monteCarloPathways.top_3_pathways || []).map((pathway: any, idx: number) => {
                                  const survivalProb = pathway.expected_outcomes?.survival_prob?.mean ?? 0
                                  const timeToStability = pathway.expected_outcomes?.time_to_stability_hr?.mean ?? 0
                                  const abxCoverage = (pathway.treatment_details?.antibiotics?.coverage || '').toLowerCase()
                                  const vasopressorType = (pathway.treatment_details?.vasopressor?.type || '').toLowerCase()
                                  const hasAntibiotics = abxCoverage !== 'none' && abxCoverage !== ''
                                  const hasVasopressors = vasopressorType !== 'none' && vasopressorType !== ''
                                  const samples = pathway.samples || monteCarloPathways.simulation_params?.samples_per_pathway || 500
                                  
                                  const optimalPathway = monteCarloPathways.top_3_pathways[0]
                                  const survivalDelta = idx > 0 ? (survivalProb - (optimalPathway.expected_outcomes?.survival_prob?.mean ?? 0)) * 100 : 0
                                  const timeDelta = idx > 0 ? (timeToStability - (optimalPathway.expected_outcomes?.time_to_stability_hr?.mean ?? 0)) : 0
                                  
                                  return (
                                    <button
                                      key={idx}
                                      onClick={() => {
                                        setSelectedPathway(idx)
                                        setWhatIfIntervention({
                                          fluids_ml: pathway.treatment_details?.fluids?.volume_ml || 0,
                                          oxygen_increase: 0,
                                          antibiotics_given: hasAntibiotics,
                                          vasopressors_started: hasVasopressors
                                        })
                                      }}
                                      className={`p-3 rounded-lg border-2 transition-all ${
                                        selectedPathway === idx
                                          ? 'border-cyan-500 bg-cyan-900/30'
                                          : 'border-gray-600 bg-gray-800/50 hover:border-gray-500'
                                      }`}
                                    >
                                      <div className="flex items-center justify-between mb-2">
                                        <div className="flex items-center gap-1">
                                          <div className="text-xs font-semibold text-white">
                                            {idx === 0 ? '🏆 Optimal' : `Option ${idx + 1}`}
                                          </div>
                                          <div className="text-[10px] text-gray-500">(n={samples})</div>
                                        </div>
                                        <div className="flex items-center gap-1">
                                          <div className="text-lg font-bold text-cyan-400">
                                            {Math.round(survivalProb * 100)}%
                                          </div>
                                          {idx > 0 && Math.abs(survivalDelta) > 0.5 && (
                                            <div className={`text-[10px] px-1 rounded ${survivalDelta < 0 ? 'bg-red-900/50 text-red-400' : 'bg-green-900/50 text-green-400'}`}>
                                              {survivalDelta > 0 ? '+' : ''}{survivalDelta.toFixed(1)}%
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                      <div className="text-xs text-gray-400 mb-1">
                                        {pathway.treatment_details?.fluids?.volume_ml || 0} mL fluids
                                      </div>
                                      <div className="text-xs text-gray-400">
                                        {hasAntibiotics ? '✓ Antibiotics' : '○ No antibiotics'}
                                        {' • '}
                                        {hasVasopressors ? '✓ Pressors' : '○ No pressors'}
                                      </div>
                                      <div className="flex items-center gap-1 text-xs text-gray-500 mt-1">
                                        <span>Stability: {timeToStability > 0 ? timeToStability.toFixed(1) : 'N/A'}h</span>
                                        {idx > 0 && Math.abs(timeDelta) > 0.5 && (
                                          <span className={`text-[10px] px-1 rounded ${timeDelta > 0 ? 'bg-red-900/50 text-red-400' : 'bg-green-900/50 text-green-400'}`}>
                                            {timeDelta > 0 ? '+' : ''}{timeDelta.toFixed(1)}h
                                          </span>
                                        )}
                                      </div>
                                    </button>
                                  )
                                })}
                              </div>
                            </div>

                            <div className="border-t border-gray-700 pt-3">
                              <div className="text-xs text-gray-400 mb-3">Adjust Parameters</div>
                              <div className="space-y-3">
                                <div>
                                  <label className="text-xs text-gray-400 mb-1 block">IV Fluids (mL)</label>
                                  <input
                                    type="range"
                                    min="0"
                                    max="4000"
                                    step="500"
                                    value={whatIfIntervention.fluids_ml}
                                    onChange={(e) => {
                                      setWhatIfIntervention({ ...whatIfIntervention, fluids_ml: parseInt(e.target.value) })
                                    }}
                                    className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                                  />
                                  <div className="text-xs text-white mt-1">{whatIfIntervention.fluids_ml} mL</div>
                                </div>
                                
                                <div className="flex space-x-4">
                                  <label className="flex items-center space-x-2 cursor-pointer">
                                    <input
                                      type="checkbox"
                                      checked={whatIfIntervention.antibiotics_given}
                                      onChange={(e) => {
                                        setWhatIfIntervention({ ...whatIfIntervention, antibiotics_given: e.target.checked })
                                      }}
                                      className="w-4 h-4 rounded border-gray-600 bg-gray-700"
                                    />
                                    <span className="text-xs text-white">Antibiotics</span>
                                  </label>
                                  
                                  <label className="flex items-center space-x-2 cursor-pointer">
                                    <input
                                      type="checkbox"
                                      checked={whatIfIntervention.vasopressors_started}
                                      onChange={(e) => {
                                        setWhatIfIntervention({ ...whatIfIntervention, vasopressors_started: e.target.checked })
                                      }}
                                      className="w-4 h-4 rounded border-gray-600 bg-gray-700"
                                    />
                                    <span className="text-xs text-white">Vasopressors</span>
                                  </label>
                                </div>

                                <button
                                  onClick={async () => {
                                    setLoadingWhatIf(true)
                                    try {
                                      const response = await fetch(`${API_URL}/api/patients/${quickViewPatient.id}/what-if/evaluate`, {
                                        method: 'POST',
                                        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
                                        body: JSON.stringify({
                                          fluids_ml: whatIfIntervention.fluids_ml,
                                          antibiotics: whatIfIntervention.antibiotics_given,
                                          vasopressors: whatIfIntervention.vasopressors_started,
                                          samples: 30
                                        })
                                      })
                                      const data = await response.json()
                                      setWhatIfPrediction(data)
                                    } catch (error) {
                                      console.error('Error evaluating custom parameters:', error)
                                    } finally {
                                      setLoadingWhatIf(false)
                                    }
                                  }}
                                  className="w-full px-4 py-2 bg-cyan-600 hover:bg-cyan-700 text-white text-xs font-medium rounded-lg transition-colors"
                                >
                                  Preview with my changes
                                </button>

                                {loadingWhatIf && (
                                  <div className="text-xs text-gray-400 text-center">
                                    Running simulation...
                                  </div>
                                )}

                                {whatIfPrediction && (
                                  <div className="p-3 bg-gray-800/50 rounded border border-gray-700">
                                    <div className="text-xs text-gray-400 mb-2">Custom Preview Results</div>
                                    <div className="grid grid-cols-3 gap-2">
                                      <div>
                                        <div className="text-xs text-gray-500">Survival</div>
                                        <div className="text-sm font-bold text-green-400">
                                          {Math.round((whatIfPrediction.survival_probability ?? 0) * 100)}%
                                        </div>
                                      </div>
                                      <div>
                                        <div className="text-xs text-gray-500">Stability</div>
                                        <div className="text-sm font-bold text-cyan-400">
                                          {(whatIfPrediction.time_to_stability_hours ?? 0) > 0 ? (whatIfPrediction.time_to_stability_hours).toFixed(1) : 'N/A'}h
                                        </div>
                                      </div>
                                      <div>
                                        <div className="text-xs text-gray-500">Organ Score</div>
                                        <div className="text-sm font-bold text-blue-400">
                                          {Math.round(whatIfPrediction.organ_preservation_score ?? 0)}%
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                )}
                              </div>
                            </div>

                            <div className="border-t border-gray-700 pt-3">
                              <div className="text-xs text-gray-400 mb-3">Outcome Comparison</div>
                              <div className="space-y-3">
                                <div>
                                  <div className="flex justify-between text-xs mb-1">
                                    <span className="text-gray-400">Survival Probability</span>
                                  </div>
                                  <div className="space-y-1">
                                    {(monteCarloPathways.top_3_pathways || []).map((pathway: any, idx: number) => {
                                      const survivalProb = pathway.expected_outcomes?.survival_prob?.mean ?? 0
                                      const survivalPct = Math.max(0, Math.min(100, survivalProb * 100))
                                      return (
                                        <div key={idx} className="flex items-center space-x-2">
                                          <div className="text-xs text-gray-500 w-16">
                                            {idx === 0 ? 'Optimal' : `Option ${idx + 1}`}
                                          </div>
                                          <div className="flex-1 bg-gray-800 rounded-full h-4 overflow-hidden">
                                            <div
                                              className={`h-full ${
                                                idx === 0 ? 'bg-green-500' : idx === 1 ? 'bg-cyan-500' : 'bg-blue-500'
                                              }`}
                                              style={{ width: `${survivalPct}%` }}
                                            />
                                          </div>
                                          <div className="text-xs text-white w-12 text-right">
                                            {Math.round(survivalPct)}%
                                          </div>
                                        </div>
                                      )
                                    })}
                                  </div>
                                </div>

                                <div>
                                  <div className="flex justify-between text-xs mb-1">
                                    <span className="text-gray-400">Time to Stability (hours)</span>
                                  </div>
                                  <div className="space-y-1">
                                    {(monteCarloPathways.top_3_pathways || []).map((pathway: any, idx: number) => {
                                      const maxTime = Math.max(...(monteCarloPathways.top_3_pathways || []).map((p: any) => p.expected_outcomes?.time_to_stability_hr?.mean || 0))
                                      const time = pathway.expected_outcomes?.time_to_stability_hr?.mean || 0
                                      return (
                                        <div key={idx} className="flex items-center space-x-2">
                                          <div className="text-xs text-gray-500 w-16">
                                            {idx === 0 ? 'Optimal' : `Option ${idx + 1}`}
                                          </div>
                                          <div className="flex-1 bg-gray-800 rounded-full h-4 overflow-hidden">
                                            <div
                                              className={`h-full ${
                                                idx === 0 ? 'bg-green-500' : idx === 1 ? 'bg-cyan-500' : 'bg-blue-500'
                                              }`}
                                              style={{ width: `${maxTime > 0 ? (time / maxTime) * 100 : 0}%` }}
                                            />
                                          </div>
                                          <div className="text-xs text-white w-12 text-right">
                                            {time.toFixed(1)}h
                                          </div>
                                        </div>
                                      )
                                    })}
                                  </div>
                                </div>

                                <div>
                                  <div className="flex justify-between text-xs mb-1">
                                    <span className="text-gray-400">Organ Preservation Score</span>
                                  </div>
                                  <div className="space-y-1">
                                    {(monteCarloPathways.top_3_pathways || []).map((pathway: any, idx: number) => {
                                      const organScore = pathway.expected_outcomes?.organ_preservation_score?.mean ?? 0
                                      const organPct = Math.max(0, Math.min(100, organScore))
                                      return (
                                        <div key={idx} className="flex items-center space-x-2">
                                          <div className="text-xs text-gray-500 w-16">
                                            {idx === 0 ? 'Optimal' : `Option ${idx + 1}`}
                                          </div>
                                          <div className="flex-1 bg-gray-800 rounded-full h-4 overflow-hidden">
                                            <div
                                              className={`h-full ${
                                                idx === 0 ? 'bg-green-500' : idx === 1 ? 'bg-cyan-500' : 'bg-blue-500'
                                              }`}
                                              style={{ width: `${organPct}%` }}
                                            />
                                          </div>
                                          <div className="text-xs text-white w-12 text-right">
                                            {Math.round(organPct)}%
                                          </div>
                                        </div>
                                      )
                                    })}
                                  </div>
                                </div>
                              </div>
                            </div>

                            <div className="text-xs text-gray-500 italic">
                              Based on {monteCarloPathways.simulation_params?.samples_per_pathway || monteCarloPathways.top_3_pathways?.[0]?.samples || 100} Monte Carlo simulations per pathway
                            </div>
                          </div>
                        ) : (
                          <div className="text-xs text-gray-400 text-center py-4">
                            No Monte Carlo pathways available
                          </div>
                        )}
                      </div>
                    </div>

                    {earlyWarning && (
                      <div className="border-t border-gray-700 pt-4">
                        <div className="flex items-center space-x-2 mb-3">
                          <Stethoscope className="w-5 h-5 text-purple-400" />
                          <h3 className="text-sm font-semibold text-white">Multi-Agent Early Warning System</h3>
                        </div>
                        <div className="bg-slate-900/70 border border-slate-600 rounded-lg p-4">
                          <div className="flex items-center justify-between mb-4">
                            <div>
                              <div className="text-xs text-gray-400 mb-1">Overall EWS Score</div>
                              <div className={`text-3xl font-bold ${
                                earlyWarning.overall_ews_score >= 70 ? 'text-red-400' : 
                                earlyWarning.overall_ews_score >= 50 ? 'text-amber-400' : 'text-green-400'
                              }`}>
                                {earlyWarning.overall_ews_score}
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="text-xs text-gray-400 mb-1">Trend</div>
                              <div className={`text-sm font-semibold ${
                                earlyWarning.trend === 'rising' ? 'text-red-400' : 
                                earlyWarning.trend === 'falling' ? 'text-green-400' : 'text-gray-400'
                              }`}>
                                {earlyWarning.trend}
                              </div>
                            </div>
                          </div>
                          
                          {earlyWarning.agent_evidence && earlyWarning.agent_evidence.length > 0 && (
                            <div className="space-y-2 mb-4">
                              <div className="text-xs text-gray-400 mb-2">Agent Evidence</div>
                              <div className="grid grid-cols-2 gap-2">
                                {earlyWarning.agent_evidence.map((agent: any, idx: number) => (
                                  <div key={idx} className={`p-2 rounded border ${
                                    agent.severity === 'critical' ? 'bg-red-950/30 border-red-600/40' :
                                    agent.severity === 'warning' ? 'bg-amber-950/30 border-amber-600/40' :
                                    agent.severity === 'info' ? 'bg-sky-950/40 border-sky-600/40' :
                                    'bg-emerald-950/30 border-emerald-600/40'
                                  }`}>
                                    <div className="flex items-center justify-between mb-1">
                                      <div className="text-xs font-semibold text-white">{agent.agent}</div>
                                      <div className={`text-sm font-bold ${
                                        agent.score >= 70 ? 'text-red-400' : 
                                        agent.score >= 50 ? 'text-amber-400' : 'text-green-400'
                                      }`}>
                                        {agent.score}
                                      </div>
                                    </div>
                                    {agent.reasons && agent.reasons.length > 0 && (
                                      <div className="text-xs text-gray-300 mt-1">
                                        {agent.reasons[0]}
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          
                          {earlyWarning.conflicts && earlyWarning.conflicts.length > 0 && (
                            <div className="mb-4 p-2 bg-amber-950/30 border border-amber-600/40 rounded text-xs text-amber-300">
                              ⚠ Agent Conflicts: {earlyWarning.conflicts[0].reason}
                            </div>
                          )}
                          
                          {earlyWarning.clinical_reasoning && (
                            <div className="text-xs text-gray-300 italic">
                              {earlyWarning.clinical_reasoning}
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </>
                )}

                <div className="flex space-x-3">
                  <Button
                    onClick={() => {
                      setSelectedPatient(quickViewPatient)
                      setCurrentView('chat')
                      setQuickViewOpen(false)
                    }}
                    className="flex-1 bg-teams-purple hover:bg-purple-700 text-white"
                  >
                    <MessageSquare className="w-4 h-4 mr-2" />
                    Open Chat
                  </Button>
                  <Button
                    onClick={() => {
                      setCurrentView('table')
                      setQuickViewOpen(false)
                    }}
                    variant="outline"
                    className="flex-1 border-gray-600 text-gray-300 hover:bg-dark-hover"
                  >
                    <TableIcon className="w-4 h-4 mr-2" />
                    View in Table
                  </Button>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default App
