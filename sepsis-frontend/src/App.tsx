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
  const [currentView, setCurrentView] = useState<'worklist' | 'watchlist' | 'featured' | 'table' | 'chat' | 'rl-analytics' | 'report' | 'dashboard'>('worklist')
  const [worklistData, setWorklistData] = useState<any[]>([])
  const [watchlistData, setWatchlistData] = useState<any[]>([])
  const [featuredPatients, setFeaturedPatients] = useState<any[]>([])
  const [selectedJourney, setSelectedJourney] = useState<any>(null)
  const [loadingWorklist, setLoadingWorklist] = useState(false)
  const [loadingWatchlist, setLoadingWatchlist] = useState(false)
  const [loadingFeatured, setLoadingFeatured] = useState(false)
  const [loadingJourney, setLoadingJourney] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [chatMessages, setChatMessages] = useState<Array<{ role: string; content: string }>>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [sortColumn, setSortColumn] = useState<string>('risk_score')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  const [filterRisk, setFilterRisk] = useState<string>('all')
  const [filterDataset, setFilterDataset] = useState<string>('all')
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
  const [reportData, setReportData] = useState<any>(null)
  const [loadingReport, setLoadingReport] = useState(false)
  const [monteCarloPathways, setMonteCarloPathways] = useState<any>(null)
  const [selectedPathway, setSelectedPathway] = useState<number>(0)
  const [loadingMonteCarlo, setLoadingMonteCarlo] = useState(false)
  const [comprehensiveData, setComprehensiveData] = useState<any>(null)
  const [multiAgentAnalysis, setMultiAgentAnalysis] = useState<any>(null)
  const [loadingComprehensive, setLoadingComprehensive] = useState(false)
  const [loadingMultiAgent, setLoadingMultiAgent] = useState(false)
  const [activeParamCategory, setActiveParamCategory] = useState<string>('vitals')
  const [alertExplanation, setAlertExplanation] = useState<any>(null)
  const [bundleTimeline, setBundleTimeline] = useState<any>(null)
  const [loadingAlertExplanation, setLoadingAlertExplanation] = useState(false)
  const [loadingBundleTimeline, setLoadingBundleTimeline] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const mediaStreamRef = useRef<MediaStream | null>(null)
  const aguiClientRef = useRef<AGUIClient | null>(null)

    useEffect(() => {
      fetchPatients()
      fetchWorklist()
      fetchWatchlist()
      fetchFeaturedPatients()
    }, [])

    const fetchWorklist = async () => {
      setLoadingWorklist(true)
      try {
        const response = await fetch(`${API_URL}/api/sepsis-worklist`, {
          headers: getAuthHeaders()
        })
        const data = await response.json()
        setWorklistData(data.worklist || [])
      } catch (error) {
        console.error('Error fetching worklist:', error)
      } finally {
        setLoadingWorklist(false)
      }
    }

    const fetchWatchlist = async () => {
      setLoadingWatchlist(true)
      try {
        const response = await fetch(`${API_URL}/api/watchlist-patients`, {
          headers: getAuthHeaders()
        })
        const data = await response.json()
        setWatchlistData(data.watchlist || [])
      } catch (error) {
        console.error('Error fetching watchlist:', error)
      } finally {
        setLoadingWatchlist(false)
      }
    }

    const fetchFeaturedPatients = async () => {
      setLoadingFeatured(true)
      try {
        const response = await fetch(`${API_URL}/api/featured-patients`, {
          headers: getAuthHeaders()
        })
        const data = await response.json()
        setFeaturedPatients(data.patients || [])
      } catch (error) {
        console.error('Error fetching featured patients:', error)
      } finally {
        setLoadingFeatured(false)
      }
    }

    const fetchPatientJourney = async (patientId: string) => {
      setLoadingJourney(true)
      try {
        const response = await fetch(`${API_URL}/api/patients/${patientId}/journey-120hr`, {
          headers: getAuthHeaders()
        })
        const data = await response.json()
        setSelectedJourney(data)
      } catch (error) {
        console.error('Error fetching patient journey:', error)
      } finally {
        setLoadingJourney(false)
      }
    }

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  useEffect(() => {
    if (currentView === 'rl-analytics' && !rlResults && !loadingRlResults) {
      fetchRlResults()
    }
    if (currentView === 'report' && !reportData && !loadingReport) {
      fetchReportData()
    }
  }, [currentView, rlResults, loadingRlResults, reportData, loadingReport])

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

  const fetchReportData = async () => {
    setLoadingReport(true)
    try {
      const response = await fetch(`${API_URL}/api/validation-reports`, {
        headers: getAuthHeaders()
      })
      const data = await response.json()
      setReportData(data)
    } catch (error) {
      console.error('Error fetching validation reports:', error)
    } finally {
      setLoadingReport(false)
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

    if (filterDataset !== 'all') {
      filtered = filtered.filter(p => {
        const cohortTags = (p as any).cohort_tags || []
        if (filterDataset === 'kaggle') {
          return cohortTags.includes('kaggle')
        } else if (filterDataset === 'synthetic') {
          return cohortTags.includes('synthetic')
        }
        return true
      })
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
        aVal = a.vitals?.current?.heart_rate ?? 0
        bVal = b.vitals?.current?.heart_rate ?? 0
      } else if (sortColumn === 'temperature') {
        aVal = a.vitals?.current?.temperature ?? 0
        bVal = b.vitals?.current?.temperature ?? 0
      } else if (sortColumn === 'wbc') {
        aVal = a.labs?.current?.wbc ?? 0
        bVal = b.labs?.current?.wbc ?? 0
      } else if (sortColumn === 'lactate') {
        aVal = a.labs?.current?.lactate ?? 0
        bVal = b.labs?.current?.lactate ?? 0
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
    setComprehensiveData(null)
    setMultiAgentAnalysis(null)
    setActiveParamCategory('vitals')
    setAlertExplanation(null)
    setBundleTimeline(null)
    setLoadingHistory(true)
    setLoadingAnalysis(true)
    setLoadingGameChangers(true)
    setLoadingMonteCarlo(true)
    setLoadingComprehensive(true)
    setLoadingMultiAgent(true)
    setLoadingAlertExplanation(true)
    setLoadingBundleTimeline(true)

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

    try {
      const comprehensiveRes = await fetch(`${API_URL}/api/patients/${patient.id}/comprehensive-data`, {
        headers: getAuthHeaders()
      })
      const comprehensiveDataResult = await comprehensiveRes.json()
      setComprehensiveData(comprehensiveDataResult)
      setLoadingComprehensive(false)
    } catch (error) {
      console.error('Error fetching comprehensive data:', error)
      setLoadingComprehensive(false)
    }

    try {
      const multiAgentRes = await fetch(`${API_URL}/api/patients/${patient.id}/multi-agent-analysis`, {
        headers: getAuthHeaders()
      })
      const multiAgentData = await multiAgentRes.json()
      setMultiAgentAnalysis(multiAgentData)
      setLoadingMultiAgent(false)
    } catch (error) {
      console.error('Error fetching multi-agent analysis:', error)
      setLoadingMultiAgent(false)
    }

    try {
      const alertExplanationRes = await fetch(`${API_URL}/api/patients/${patient.id}/alert-explanation`, {
        headers: getAuthHeaders()
      })
      const alertExplanationData = await alertExplanationRes.json()
      setAlertExplanation(alertExplanationData)
      setLoadingAlertExplanation(false)
    } catch (error) {
      console.error('Error fetching alert explanation:', error)
      setLoadingAlertExplanation(false)
    }

    try {
      const bundleTimelineRes = await fetch(`${API_URL}/api/patients/${patient.id}/sepsis-bundle-timeline`, {
        headers: getAuthHeaders()
      })
      const bundleTimelineData = await bundleTimelineRes.json()
      setBundleTimeline(bundleTimelineData)
      setLoadingBundleTimeline(false)
    } catch (error) {
      console.error('Error fetching bundle timeline:', error)
      setLoadingBundleTimeline(false)
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
                <div className="flex space-x-1 overflow-x-auto">
                  <button
                    onClick={() => setCurrentView('worklist')}
                    className={`px-4 py-3 font-medium transition-colors whitespace-nowrap ${
                      currentView === 'worklist'
                        ? 'text-teams-purple border-b-2 border-teams-purple'
                        : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    <AlertTriangle className="w-4 h-4 inline mr-2" />
                    Worklist
                  </button>
                  <button
                    onClick={() => setCurrentView('watchlist')}
                    className={`px-4 py-3 font-medium transition-colors whitespace-nowrap ${
                      currentView === 'watchlist'
                        ? 'text-teams-purple border-b-2 border-teams-purple'
                        : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    <Clock className="w-4 h-4 inline mr-2" />
                    Watchlist
                  </button>
                  <button
                    onClick={() => setCurrentView('featured')}
                    className={`px-4 py-3 font-medium transition-colors whitespace-nowrap ${
                      currentView === 'featured'
                        ? 'text-teams-purple border-b-2 border-teams-purple'
                        : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    <Stethoscope className="w-4 h-4 inline mr-2" />
                    Featured Cases
                  </button>
                  <button
                    onClick={() => setCurrentView('table')}
                    className={`px-4 py-3 font-medium transition-colors whitespace-nowrap ${
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
                    className={`px-4 py-3 font-medium transition-colors whitespace-nowrap ${
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
                    className={`px-4 py-3 font-medium transition-colors whitespace-nowrap ${
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
                    className={`px-4 py-3 font-medium transition-colors whitespace-nowrap ${
                      currentView === 'report'
                        ? 'text-teams-purple border-b-2 border-teams-purple'
                        : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    <TrendingUp className="w-4 h-4 inline mr-2" />
                    Report
                  </button>
                  <button
                    onClick={() => setCurrentView('dashboard')}
                    className={`px-4 py-3 font-medium transition-colors whitespace-nowrap ${
                      currentView === 'dashboard'
                        ? 'text-teams-purple border-b-2 border-teams-purple'
                        : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    <Users className="w-4 h-4 inline mr-2" />
                    Dashboard
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
                      {currentView === 'worklist' && (
                        <Card className="bg-dark-card border-gray-700">
                          <CardHeader>
                            <CardTitle className="flex items-center space-x-2 text-white">
                              <AlertTriangle className="w-5 h-5 text-red-500" />
                              <span>Sepsis Worklist - Immediate Attention Required</span>
                            </CardTitle>
                            <CardDescription className="text-gray-400">
                              High-risk patients prioritized by sepsis stage and risk score ({worklistData.length} patients)
                            </CardDescription>
                          </CardHeader>
                          <CardContent>
                            {loadingWorklist ? (
                              <div className="space-y-4">
                                {[1, 2, 3].map(i => <Skeleton key={i} className="h-32 w-full bg-gray-700" />)}
                              </div>
                            ) : worklistData.length === 0 ? (
                              <div className="text-center py-8 text-gray-400">
                                <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-green-500" />
                                <p>No high-risk patients currently on worklist</p>
                              </div>
                            ) : (
                              <ScrollArea className="h-[600px]">
                                <div className="space-y-4">
                                  {worklistData.map((item: any, index: number) => (
                                    <div
                                      key={item.id}
                                      className="p-4 bg-dark-hover border border-red-800 rounded-lg cursor-pointer hover:border-red-600 transition-colors"
                                      onClick={() => {
                                        const patient = patients.find(p => p.id === item.id)
                                        if (patient) openPatientDetails(patient)
                                      }}
                                    >
                                      <div className="flex items-start justify-between mb-3">
                                        <div className="flex items-center space-x-3">
                                          <div className="w-8 h-8 rounded-full bg-red-600 flex items-center justify-center text-white font-bold text-sm">
                                            {index + 1}
                                          </div>
                                          <div>
                                            <h3 className="font-semibold text-white">{item.name}</h3>
                                            <p className="text-sm text-gray-400">{item.room} | MRN: {item.mrn}</p>
                                          </div>
                                        </div>
                                        <div className="text-right">
                                          <Badge className={`${item.sepsis_stage_num >= 3 ? 'bg-red-600' : item.sepsis_stage_num >= 2 ? 'bg-orange-500' : 'bg-yellow-500'} text-white`}>
                                            {item.sepsis_stage}
                                          </Badge>
                                          <p className="text-xs text-gray-400 mt-1">Risk: {item.risk_score}</p>
                                        </div>
                                      </div>
                            
                                      <div className="grid grid-cols-4 gap-4 mb-3">
                                        <div className="bg-dark p-2 rounded border border-gray-700">
                                          <p className="text-xs text-gray-500">SIRS</p>
                                          <p className="text-lg font-bold text-white">{item.sirs_count}/4</p>
                                        </div>
                                        <div className="bg-dark p-2 rounded border border-gray-700">
                                          <p className="text-xs text-gray-500">Lactate</p>
                                          <p className="text-lg font-bold text-white">{item.lactate?.toFixed(1) || 'N/A'}</p>
                                        </div>
                                        <div className="bg-dark p-2 rounded border border-gray-700">
                                          <p className="text-xs text-gray-500">HR</p>
                                          <p className="text-lg font-bold text-white">{item.vitals?.heart_rate || 'N/A'}</p>
                                        </div>
                                        <div className="bg-dark p-2 rounded border border-gray-700">
                                          <p className="text-xs text-gray-500">Temp</p>
                                          <p className="text-lg font-bold text-white">{item.vitals?.temperature?.toFixed(1) || 'N/A'}°C</p>
                                        </div>
                                      </div>
                            
                                      <div className="flex items-center justify-between">
                                        <div className="flex-1">
                                          <p className="text-sm text-gray-300"><span className="text-gray-500">Diagnosis:</span> {item.diagnosis}</p>
                                          <p className="text-sm text-yellow-400 mt-1"><span className="text-gray-500">Risk Reason:</span> {item.risk_reason}</p>
                                        </div>
                                        <Button 
                                          variant="outline" 
                                          size="sm" 
                                          className="border-teams-purple text-teams-purple hover:bg-teams-purple hover:text-white"
                                          onClick={(e) => {
                                            e.stopPropagation()
                                            fetchPatientJourney(item.id)
                                          }}
                                        >
                                          View 120hr Journey
                                        </Button>
                                      </div>
                            
                                      {item.notes && item.notes.length > 0 && (
                                        <div className="mt-3 pt-3 border-t border-gray-700">
                                          <p className="text-xs text-gray-500 mb-1">Latest Note:</p>
                                          <p className="text-sm text-gray-300">{item.notes[0]?.note}</p>
                                        </div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </ScrollArea>
                            )}
                          </CardContent>
                        </Card>
                      )}

                      {currentView === 'watchlist' && (
                        <Card className="bg-dark-card border-gray-700">
                          <CardHeader>
                            <CardTitle className="flex items-center space-x-2 text-white">
                              <Clock className="w-5 h-5 text-yellow-500" />
                              <span>Watchlist - Monitor Closely</span>
                            </CardTitle>
                            <CardDescription className="text-gray-400">
                              Sub-threshold patients with concerning signs ({watchlistData.length} patients)
                            </CardDescription>
                          </CardHeader>
                          <CardContent>
                            {loadingWatchlist ? (
                              <div className="space-y-4">
                                {[1, 2, 3].map(i => <Skeleton key={i} className="h-24 w-full bg-gray-700" />)}
                              </div>
                            ) : watchlistData.length === 0 ? (
                              <div className="text-center py-8 text-gray-400">
                                <CheckCircle2 className="w-12 h-12 mx-auto mb-4 text-green-500" />
                                <p>No patients currently on watchlist</p>
                                <p className="text-sm mt-2">All moderate-risk patients are stable</p>
                              </div>
                            ) : (
                              <ScrollArea className="h-[600px]">
                                <div className="space-y-4">
                                  {watchlistData.map((item: any) => (
                                    <div
                                      key={item.id}
                                      className="p-4 bg-dark-hover border border-yellow-800 rounded-lg cursor-pointer hover:border-yellow-600 transition-colors"
                                      onClick={() => {
                                        const patient = patients.find(p => p.id === item.id)
                                        if (patient) openPatientDetails(patient)
                                      }}
                                    >
                                      <div className="flex items-start justify-between mb-3">
                                        <div>
                                          <h3 className="font-semibold text-white">{item.name}</h3>
                                          <p className="text-sm text-gray-400">{item.room} | MRN: {item.mrn}</p>
                                        </div>
                                        <Badge className="bg-yellow-600 text-white">WATCH</Badge>
                                      </div>
                            
                                      <p className="text-sm text-yellow-400 mb-3">{item.watch_reason}</p>
                            
                                      <div className="bg-dark p-3 rounded border border-gray-700">
                                        <p className="text-xs text-gray-500 mb-2">Recommended Actions:</p>
                                        <ul className="space-y-1">
                                          {item.recommended_actions?.map((action: string, i: number) => (
                                            <li key={i} className="text-sm text-gray-300 flex items-center">
                                              <span className="w-1.5 h-1.5 bg-yellow-500 rounded-full mr-2"></span>
                                              {action}
                                            </li>
                                          ))}
                                        </ul>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </ScrollArea>
                            )}
                          </CardContent>
                        </Card>
                      )}

                      {currentView === 'featured' && (
                        <div className="space-y-6">
                          <Card className="bg-dark-card border-gray-700">
                            <CardHeader>
                              <CardTitle className="flex items-center space-x-2 text-white">
                                <Stethoscope className="w-5 h-5 text-teams-purple" />
                                <span>Featured Clinical Cases - 120hr Patient Journey</span>
                              </CardTitle>
                              <CardDescription className="text-gray-400">
                                4 realistic sepsis presentations with comprehensive EHR data
                              </CardDescription>
                            </CardHeader>
                            <CardContent>
                              {loadingFeatured ? (
                                <div className="grid grid-cols-2 gap-4">
                                  {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-48 w-full bg-gray-700" />)}
                                </div>
                              ) : (
                                <div className="grid grid-cols-2 gap-4">
                                  {featuredPatients.map((patient: any) => (
                                    <div
                                      key={patient.id}
                                      className={`p-4 bg-dark-hover border rounded-lg cursor-pointer transition-colors ${
                                        patient.sepsis_stage_num >= 3 ? 'border-red-700 hover:border-red-500' :
                                        patient.sepsis_stage_num >= 2 ? 'border-orange-700 hover:border-orange-500' :
                                        'border-yellow-700 hover:border-yellow-500'
                                      }`}
                                      onClick={() => fetchPatientJourney(patient.id)}
                                    >
                                      <div className="flex items-start justify-between mb-3">
                                        <div>
                                          <h3 className="font-semibold text-white">{patient.name}</h3>
                                          <p className="text-sm text-gray-400">{patient.age}yo {patient.gender} | {patient.room}</p>
                                        </div>
                                        <div className="text-right">
                                          <Badge className={`${
                                            patient.risk_level === 'CRITICAL' ? 'bg-red-600' :
                                            patient.risk_level === 'HIGH' ? 'bg-orange-500' :
                                            'bg-yellow-500'
                                          } text-white`}>
                                            {patient.risk_level}
                                          </Badge>
                                          <p className="text-xs text-gray-400 mt-1">Score: {patient.risk_score}</p>
                                        </div>
                                      </div>
                            
                                      <p className="text-sm text-gray-300 mb-2">{patient.diagnosis}</p>
                                      <p className="text-sm text-gray-400 mb-3">{patient.chief_complaint}</p>
                            
                                      <div className="grid grid-cols-3 gap-2 mb-3">
                                        <div className="bg-dark p-2 rounded text-center">
                                          <p className="text-xs text-gray-500">Stage</p>
                                          <p className="text-sm font-bold text-white">{patient.sepsis_stage}</p>
                                        </div>
                                        <div className="bg-dark p-2 rounded text-center">
                                          <p className="text-xs text-gray-500">SIRS</p>
                                          <p className="text-sm font-bold text-white">{patient.sirs_criteria}/4</p>
                                        </div>
                                        <div className="bg-dark p-2 rounded text-center">
                                          <p className="text-xs text-gray-500">Lactate</p>
                                          <p className="text-sm font-bold text-white">{patient.labs?.current?.lactate?.toFixed(1)}</p>
                                        </div>
                                      </div>
                            
                                      <div className="flex items-center justify-between">
                                        <p className="text-xs text-gray-500">
                                          Attending: {patient.attending_physician}
                                        </p>
                                        <Button 
                                          variant="outline" 
                                          size="sm" 
                                          className="border-teams-purple text-teams-purple hover:bg-teams-purple hover:text-white"
                                        >
                                          View Journey
                                        </Button>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </CardContent>
                          </Card>

                          {selectedJourney && (
                            <Card className="bg-dark-card border-gray-700">
                              <CardHeader>
                                <div className="flex items-center justify-between">
                                  <div>
                                    <CardTitle className="text-white">
                                      120-Hour Patient Journey: {selectedJourney.patient?.name}
                                    </CardTitle>
                                    <CardDescription className="text-gray-400">
                                      {selectedJourney.patient?.diagnosis} | {selectedJourney.patient?.room}
                                    </CardDescription>
                                  </div>
                                  <Button 
                                    variant="ghost" 
                                    size="sm" 
                                    className="text-gray-400 hover:text-white"
                                    onClick={() => setSelectedJourney(null)}
                                  >
                                    Close
                                  </Button>
                                </div>
                              </CardHeader>
                              <CardContent>
                                {loadingJourney ? (
                                  <Skeleton className="h-96 w-full bg-gray-700" />
                                ) : (
                                  <Tabs defaultValue="vitals" className="w-full">
                                    <TabsList className="bg-dark border border-gray-700">
                                      <TabsTrigger value="vitals" className="data-[state=active]:bg-teams-purple">Vitals Trend</TabsTrigger>
                                      <TabsTrigger value="labs" className="data-[state=active]:bg-teams-purple">Labs Trend</TabsTrigger>
                                      <TabsTrigger value="meds" className="data-[state=active]:bg-teams-purple">Medications</TabsTrigger>
                                      <TabsTrigger value="notes" className="data-[state=active]:bg-teams-purple">Notes</TabsTrigger>
                                      <TabsTrigger value="bundle" className="data-[state=active]:bg-teams-purple">Sepsis Bundle</TabsTrigger>
                                    </TabsList>
                          
                                    <TabsContent value="vitals" className="mt-4">
                                      <div className="h-80">
                                        <ResponsiveContainer width="100%" height="100%">
                                          <LineChart data={selectedJourney.vitals_history?.slice(-30) || []}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                            <XAxis 
                                              dataKey="timestamp" 
                                              stroke="#9CA3AF"
                                              tickFormatter={(val) => new Date(val).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                                            />
                                            <YAxis stroke="#9CA3AF" />
                                            <Tooltip 
                                              contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                                              labelStyle={{ color: '#9CA3AF' }}
                                            />
                                            <Legend />
                                            <Line type="monotone" dataKey="heart_rate" stroke="#EF4444" name="HR" dot={false} />
                                            <Line type="monotone" dataKey="respiratory_rate" stroke="#F59E0B" name="RR" dot={false} />
                                            <Line type="monotone" dataKey="spo2" stroke="#10B981" name="SpO2" dot={false} />
                                          </LineChart>
                                        </ResponsiveContainer>
                                      </div>
                                      <div className="h-60 mt-4">
                                        <ResponsiveContainer width="100%" height="100%">
                                          <LineChart data={selectedJourney.vitals_history?.slice(-30) || []}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                            <XAxis 
                                              dataKey="timestamp" 
                                              stroke="#9CA3AF"
                                              tickFormatter={(val) => new Date(val).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                                            />
                                            <YAxis stroke="#9CA3AF" domain={[35, 42]} />
                                            <Tooltip 
                                              contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                                              labelStyle={{ color: '#9CA3AF' }}
                                            />
                                            <Legend />
                                            <Line type="monotone" dataKey="temperature" stroke="#8B5CF6" name="Temp (°C)" dot={false} />
                                          </LineChart>
                                        </ResponsiveContainer>
                                      </div>
                                    </TabsContent>
                          
                                    <TabsContent value="labs" className="mt-4">
                                      <div className="h-80">
                                        <ResponsiveContainer width="100%" height="100%">
                                          <LineChart data={selectedJourney.labs_history?.slice(-15) || []}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                            <XAxis 
                                              dataKey="timestamp" 
                                              stroke="#9CA3AF"
                                              tickFormatter={(val) => new Date(val).toLocaleDateString([], {month: 'short', day: 'numeric'})}
                                            />
                                            <YAxis stroke="#9CA3AF" />
                                            <Tooltip 
                                              contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                                              labelStyle={{ color: '#9CA3AF' }}
                                            />
                                            <Legend />
                                            <Line type="monotone" dataKey="lactate" stroke="#EF4444" name="Lactate" />
                                            <Line type="monotone" dataKey="wbc" stroke="#F59E0B" name="WBC" />
                                            <Line type="monotone" dataKey="creatinine" stroke="#3B82F6" name="Creatinine" />
                                          </LineChart>
                                        </ResponsiveContainer>
                                      </div>
                            
                                      <div className="mt-4 overflow-x-auto">
                                        <table className="w-full text-sm">
                                          <thead>
                                            <tr className="border-b border-gray-700">
                                              <th className="text-left p-2 text-gray-400">Time</th>
                                              <th className="text-left p-2 text-gray-400">Lactate</th>
                                              <th className="text-left p-2 text-gray-400">WBC</th>
                                              <th className="text-left p-2 text-gray-400">Creatinine</th>
                                              <th className="text-left p-2 text-gray-400">Platelets</th>
                                              <th className="text-left p-2 text-gray-400">Procalcitonin</th>
                                            </tr>
                                          </thead>
                                          <tbody>
                                            {selectedJourney.labs_history?.slice(-10).reverse().map((lab: any, i: number) => (
                                              <tr key={i} className="border-b border-gray-800">
                                                <td className="p-2 text-gray-300">{new Date(lab.timestamp).toLocaleString()}</td>
                                                <td className={`p-2 ${lab.lactate > 2 ? 'text-red-400' : 'text-gray-300'}`}>{lab.lactate?.toFixed(1)}</td>
                                                <td className={`p-2 ${lab.wbc > 12 ? 'text-yellow-400' : 'text-gray-300'}`}>{lab.wbc?.toFixed(1)}</td>
                                                <td className={`p-2 ${lab.creatinine > 1.5 ? 'text-orange-400' : 'text-gray-300'}`}>{lab.creatinine?.toFixed(1)}</td>
                                                <td className={`p-2 ${lab.platelets < 150 ? 'text-red-400' : 'text-gray-300'}`}>{lab.platelets}</td>
                                                <td className={`p-2 ${lab.procalcitonin > 2 ? 'text-red-400' : 'text-gray-300'}`}>{lab.procalcitonin?.toFixed(2)}</td>
                                              </tr>
                                            ))}
                                          </tbody>
                                        </table>
                                      </div>
                                    </TabsContent>
                          
                                    <TabsContent value="meds" className="mt-4">
                                      <div className="space-y-3">
                                        {selectedJourney.medications?.map((med: any, i: number) => (
                                          <div key={i} className="p-3 bg-dark rounded border border-gray-700">
                                            <div className="flex items-center justify-between">
                                              <div>
                                                <p className="font-semibold text-white">{med.name}</p>
                                                <p className="text-sm text-gray-400">{med.dose} | {med.route} | {med.frequency}</p>
                                              </div>
                                              <p className="text-xs text-gray-500">Started: {med.start}</p>
                                            </div>
                                          </div>
                                        ))}
                                        {(!selectedJourney.medications || selectedJourney.medications.length === 0) && (
                                          <p className="text-gray-400 text-center py-4">No medications recorded</p>
                                        )}
                                      </div>
                                    </TabsContent>
                          
                                    <TabsContent value="notes" className="mt-4">
                                      <ScrollArea className="h-80">
                                        <div className="space-y-3">
                                          {selectedJourney.notes?.map((note: any, i: number) => (
                                            <div key={i} className="p-3 bg-dark rounded border border-gray-700">
                                              <div className="flex items-center justify-between mb-2">
                                                <p className="text-sm font-semibold text-teams-purple">{note.author || 'Nurse'}</p>
                                                <p className="text-xs text-gray-500">{note.time}</p>
                                              </div>
                                              <p className="text-sm text-gray-300">{note.note}</p>
                                            </div>
                                          ))}
                                          {(!selectedJourney.notes || selectedJourney.notes.length === 0) && (
                                            <p className="text-gray-400 text-center py-4">No notes recorded</p>
                                          )}
                                        </div>
                                      </ScrollArea>
                                    </TabsContent>
                          
                                    <TabsContent value="bundle" className="mt-4">
                                      <div className="grid grid-cols-2 gap-4">
                                        {Object.entries(selectedJourney.sepsis_bundle || {}).map(([key, value]: [string, any]) => (
                                          <div key={key} className={`p-4 rounded border ${
                                            value?.status === 'complete' ? 'bg-green-900/20 border-green-700' :
                                            value?.status === 'in_progress' ? 'bg-yellow-900/20 border-yellow-700' :
                                            value?.status === 'pending' ? 'bg-red-900/20 border-red-700' :
                                            'bg-dark border-gray-700'
                                          }`}>
                                            <div className="flex items-center justify-between mb-2">
                                              <p className="font-semibold text-white capitalize">{key.replace(/_/g, ' ')}</p>
                                              {value?.status === 'complete' && <CheckCircle2 className="w-5 h-5 text-green-500" />}
                                              {value?.status === 'in_progress' && <Clock className="w-5 h-5 text-yellow-500" />}
                                              {value?.status === 'pending' && <AlertTriangle className="w-5 h-5 text-red-500" />}
                                            </div>
                                            {value?.time && <p className="text-xs text-gray-400">Time: {value.time}</p>}
                                            {value?.value && <p className="text-sm text-gray-300">Value: {value.value}</p>}
                                            {value?.volume_ml && <p className="text-sm text-gray-300">Volume: {value.volume_ml} mL</p>}
                                            {value?.agent && <p className="text-sm text-gray-300">Agent: {value.agent}</p>}
                                          </div>
                                        ))}
                                      </div>
                            
                                      {selectedJourney.patient?.problem_list && (
                                        <div className="mt-6">
                                          <h4 className="text-white font-semibold mb-3">Problem List</h4>
                                          <div className="space-y-2">
                                            {selectedJourney.patient.problem_list.map((problem: any, i: number) => (
                                              <div key={i} className="flex items-center justify-between p-2 bg-dark rounded border border-gray-700">
                                                <p className="text-sm text-gray-300">{problem.problem}</p>
                                                <Badge className={problem.status === 'Active' ? 'bg-red-600' : 'bg-gray-600'}>
                                                  {problem.status}
                                                </Badge>
                                              </div>
                                            ))}
                                          </div>
                                        </div>
                                      )}
                            
                                      {selectedJourney.patient?.allergies && selectedJourney.patient.allergies.length > 0 && (
                                        <div className="mt-6">
                                          <h4 className="text-white font-semibold mb-3">Allergies</h4>
                                          <div className="flex flex-wrap gap-2">
                                            {selectedJourney.patient.allergies.map((allergy: any, i: number) => (
                                              <Badge key={i} className="bg-red-900 text-red-200">
                                                {allergy.allergen}: {allergy.reaction}
                                              </Badge>
                                            ))}
                                          </div>
                                        </div>
                                      )}
                                    </TabsContent>
                                  </Tabs>
                                )}
                              </CardContent>
                            </Card>
                          )}
                        </div>
                      )}

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
                              <p className="text-xs font-semibold text-white">{patient.vitals?.current?.heart_rate ?? 'N/A'}</p>
                            </div>
                            <div className="bg-dark p-1 rounded border border-gray-700">
                              <p className="text-xs text-gray-500">Temp</p>
                              <p className="text-xs font-semibold text-white">{patient.vitals?.current?.temperature ? `${patient.vitals.current.temperature}°` : 'N/A'}</p>
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
                      
                      <select
                        value={filterDataset}
                        onChange={(e) => setFilterDataset(e.target.value)}
                        className="px-3 py-2 bg-dark border border-gray-600 rounded-md text-white"
                      >
                        <option value="all">All Datasets</option>
                        <option value="synthetic">Synthetic</option>
                        <option value="kaggle">Kaggle</option>
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
                            <td className="p-3 text-gray-300">{patient.vitals?.current?.heart_rate ?? 'N/A'}</td>
                            <td className="p-3 text-gray-300">{patient.vitals?.current?.temperature ? `${patient.vitals.current.temperature}°C` : 'N/A'}</td>
                            <td className="p-3 text-gray-300">{patient.labs?.current?.wbc ?? 'N/A'}</td>
                            <td className="p-3 text-gray-300">{patient.labs?.current?.lactate ?? 'N/A'}</td>
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
                      <span>Model Validation Reports</span>
                    </CardTitle>
                    <CardDescription className="text-gray-400">
                      Comprehensive validation metrics for sepsis prediction model on Kaggle and Synthetic datasets
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {loadingReport ? (
                      <div className="space-y-4">
                        <Skeleton className="h-32 w-full bg-gray-700" />
                        <Skeleton className="h-64 w-full bg-gray-700" />
                        <Skeleton className="h-64 w-full bg-gray-700" />
                      </div>
                    ) : reportData && reportData.kaggle && reportData.kaggle.threshold_metrics ? (
                      <div className="space-y-6">
                        {/* Kaggle Dataset Metrics */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <Card className="bg-dark border-gray-700">
                            <CardContent className="pt-6">
                              <div className="text-center">
                                <p className="text-xs text-gray-400 mb-2">AUROC</p>
                                <p className="text-3xl font-bold text-blue-400">
                                  {(reportData.kaggle.auroc * 100).toFixed(1)}%
                                </p>
                                <p className="text-xs text-gray-500 mt-1">Area Under ROC Curve</p>
                              </div>
                            </CardContent>
                          </Card>
                          <Card className="bg-dark border-gray-700">
                            <CardContent className="pt-6">
                              <div className="text-center">
                                <p className="text-xs text-gray-400 mb-2">AUPRC</p>
                                <p className="text-3xl font-bold text-cyan-400">
                                  {(reportData.kaggle.auprc * 100).toFixed(1)}%
                                </p>
                                <p className="text-xs text-gray-500 mt-1">Area Under PR Curve</p>
                              </div>
                            </CardContent>
                          </Card>
                          <Card className="bg-dark border-gray-700">
                            <CardContent className="pt-6">
                              <div className="text-center">
                                <p className="text-xs text-gray-400 mb-2">Dataset Size</p>
                                <p className="text-3xl font-bold text-green-400">
                                  {reportData.kaggle.n_patients.toLocaleString()}
                                </p>
                                <p className="text-xs text-gray-500 mt-1">{reportData.kaggle.n_sepsis} sepsis ({(reportData.kaggle.prevalence * 100).toFixed(1)}%)</p>
                              </div>
                            </CardContent>
                          </Card>
                        </div>

                        {/* Threshold Analysis Table */}
                        <Card className="bg-dark border-gray-700">
                          <CardHeader>
                            <CardTitle className="text-white text-lg">Threshold Analysis - Kaggle Dataset</CardTitle>
                            <CardDescription className="text-gray-400">
                              Performance metrics at different risk score thresholds (Current: threshold 50, PPV 45.5%)
                            </CardDescription>
                          </CardHeader>
                          <CardContent>
                            <div className="overflow-x-auto">
                              <table className="w-full text-sm">
                                <thead>
                                  <tr className="border-b border-gray-700">
                                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Threshold</th>
                                    <th className="text-right py-2 px-3 text-gray-400 font-medium">PPV</th>
                                    <th className="text-right py-2 px-3 text-gray-400 font-medium">Sensitivity</th>
                                    <th className="text-right py-2 px-3 text-gray-400 font-medium">Specificity</th>
                                    <th className="text-right py-2 px-3 text-gray-400 font-medium">F1</th>
                                    <th className="text-right py-2 px-3 text-gray-400 font-medium">Accuracy</th>
                                    <th className="text-right py-2 px-3 text-gray-400 font-medium">TP</th>
                                    <th className="text-right py-2 px-3 text-gray-400 font-medium">FP</th>
                                    <th className="text-right py-2 px-3 text-gray-400 font-medium">FN</th>
                                    <th className="text-right py-2 px-3 text-gray-400 font-medium">TN</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {reportData.kaggle.threshold_metrics.map((metric: any) => (
                                    <tr key={metric.threshold} className={`border-b border-gray-800 ${metric.threshold === reportData.kaggle.optimal_threshold.threshold ? 'bg-purple-950/30' : ''}`}>
                                      <td className="py-2 px-3 text-white font-semibold">{metric.threshold}</td>
                                      <td className="text-right py-2 px-3 text-white">{(metric.ppv * 100).toFixed(1)}%</td>
                                      <td className="text-right py-2 px-3 text-white">{(metric.sensitivity * 100).toFixed(1)}%</td>
                                      <td className="text-right py-2 px-3 text-white">{(metric.specificity * 100).toFixed(1)}%</td>
                                      <td className="text-right py-2 px-3 text-white">{(metric.f1 * 100).toFixed(1)}%</td>
                                      <td className="text-right py-2 px-3 text-white">{(metric.accuracy * 100).toFixed(1)}%</td>
                                      <td className="text-right py-2 px-3 text-green-400">{metric.tp}</td>
                                      <td className="text-right py-2 px-3 text-red-400">{metric.fp}</td>
                                      <td className="text-right py-2 px-3 text-orange-400">{metric.fn}</td>
                                      <td className="text-right py-2 px-3 text-gray-400">{metric.tn}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                            <div className="mt-4 p-3 bg-purple-950/30 border border-purple-600/40 rounded">
                              <p className="text-xs text-purple-300 font-semibold mb-1">Optimal Threshold (Max F1): {reportData.kaggle.optimal_threshold.threshold}</p>
                              <p className="text-xs text-gray-300">
                                PPV: {(reportData.kaggle.optimal_threshold.ppv * 100).toFixed(1)}%, 
                                Sensitivity: {(reportData.kaggle.optimal_threshold.sensitivity * 100).toFixed(1)}%, 
                                F1: {(reportData.kaggle.optimal_threshold.f1 * 100).toFixed(1)}%
                              </p>
                            </div>
                          </CardContent>
                        </Card>

                        {/* Confusion Matrix for Current Threshold */}
                        <Card className="bg-dark border-gray-700">
                          <CardHeader>
                            <CardTitle className="text-white text-lg">Confusion Matrix - Current Threshold (50)</CardTitle>
                            <CardDescription className="text-gray-400">
                              Classification results on {reportData.kaggle.n_patients.toLocaleString()} patients
                            </CardDescription>
                          </CardHeader>
                          <CardContent>
                            <div className="grid grid-cols-2 gap-4 max-w-md mx-auto">
                              <div className="bg-green-950/30 border-2 border-green-600/40 rounded-lg p-4 text-center">
                                <p className="text-xs text-gray-400 mb-1">True Positives</p>
                                <p className="text-3xl font-bold text-green-400">{reportData.kaggle.threshold_metrics.find((m: any) => m.threshold === 50)?.tp || 0}</p>
                                <p className="text-xs text-gray-500 mt-1">Correctly identified sepsis</p>
                              </div>
                              <div className="bg-red-950/30 border-2 border-red-600/40 rounded-lg p-4 text-center">
                                <p className="text-xs text-gray-400 mb-1">False Positives</p>
                                <p className="text-3xl font-bold text-red-400">{reportData.kaggle.threshold_metrics.find((m: any) => m.threshold === 50)?.fp || 0}</p>
                                <p className="text-xs text-gray-500 mt-1">False alarms</p>
                              </div>
                              <div className="bg-orange-950/30 border-2 border-orange-600/40 rounded-lg p-4 text-center">
                                <p className="text-xs text-gray-400 mb-1">False Negatives</p>
                                <p className="text-3xl font-bold text-orange-400">{reportData.kaggle.threshold_metrics.find((m: any) => m.threshold === 50)?.fn || 0}</p>
                                <p className="text-xs text-gray-500 mt-1">Missed sepsis cases</p>
                              </div>
                              <div className="bg-gray-800/50 border-2 border-gray-600/40 rounded-lg p-4 text-center">
                                <p className="text-xs text-gray-400 mb-1">True Negatives</p>
                                <p className="text-3xl font-bold text-gray-300">{reportData.kaggle.threshold_metrics.find((m: any) => m.threshold === 50)?.tn || 0}</p>
                                <p className="text-xs text-gray-500 mt-1">Correctly ruled out</p>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      </div>
                    ) : (
                      <div className="text-center py-12">
                        <TrendingUp className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                        <p className="text-gray-400 mb-2">No report data available</p>
                        <p className="text-sm text-gray-500">Unable to load trending outcomes data</p>
                      </div>
                    )}
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

                {/* Explain My Alert Card */}
                <div>
                  <div className="flex items-center space-x-2 mb-3">
                    <AlertTriangle className="w-5 h-5 text-amber-400" />
                    <h3 className="text-sm font-semibold text-white">Explain My Alert</h3>
                  </div>
                  
                  {loadingAlertExplanation ? (
                    <Skeleton className="h-40 w-full bg-gray-700 rounded-lg" />
                  ) : alertExplanation ? (
                    <div className="bg-slate-900/70 border border-slate-600 rounded-lg p-4 space-y-4">
                      <div className="border-b border-gray-700 pb-3">
                        <h4 className="text-lg font-bold text-white mb-2">{alertExplanation.headline}</h4>
                        <p className="text-sm text-gray-300">{alertExplanation.on_worklist_because}</p>
                      </div>
                      
                      {alertExplanation.key_findings && alertExplanation.key_findings.length > 0 && (
                        <div>
                          <h5 className="text-xs font-semibold text-gray-400 mb-2">Key Findings</h5>
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                            {alertExplanation.key_findings.slice(0, 6).map((finding: any, idx: number) => {
                              const concernColors: Record<string, string> = {
                                critical: 'bg-red-900/50 border-red-600/40 text-red-300',
                                high: 'bg-orange-900/50 border-orange-600/40 text-orange-300',
                                moderate: 'bg-amber-900/50 border-amber-600/40 text-amber-300',
                                low: 'bg-green-900/50 border-green-600/40 text-green-300'
                              }
                              const colorClass = concernColors[finding.concern_level] || concernColors.moderate
                              return (
                                <div key={idx} className={`rounded border p-2 ${colorClass}`}>
                                  <div className="text-xs opacity-80">{finding.finding}</div>
                                  <div className="text-sm font-semibold">{finding.value}</div>
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      )}
                      
                      {alertExplanation.agent_agreement && (
                        <div>
                          <h5 className="text-xs font-semibold text-gray-400 mb-2">
                            Agent Agreement: <span className={`ml-1 ${
                              alertExplanation.agent_agreement.consensus === 'unanimous' ? 'text-green-400' :
                              alertExplanation.agent_agreement.consensus === 'strong' ? 'text-blue-400' :
                              alertExplanation.agent_agreement.consensus === 'moderate' ? 'text-amber-400' : 'text-red-400'
                            }`}>
                              {alertExplanation.agent_agreement.agreeing_agents}/{alertExplanation.agent_agreement.total_agents} agents agree ({alertExplanation.agent_agreement.consensus})
                            </span>
                          </h5>
                          <div className="flex flex-wrap gap-1">
                            {alertExplanation.agent_agreement.agent_votes?.map((vote: any, idx: number) => {
                              const assessmentColors: Record<string, string> = {
                                critical: 'bg-red-600',
                                concerning: 'bg-orange-600',
                                elevated: 'bg-amber-600',
                                normal: 'bg-green-600',
                                stable: 'bg-blue-600'
                              }
                              const bgColor = assessmentColors[vote.assessment] || 'bg-gray-600'
                              return (
                                <div key={idx} className={`${bgColor} text-white text-xs px-2 py-1 rounded-full flex items-center gap-1`} title={vote.key_reason}>
                                  <span>{vote.agent}</span>
                                  <span className="opacity-70">({Math.round(vote.confidence * 100)}%)</span>
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      )}
                      
                      {alertExplanation.nurse_actions && alertExplanation.nurse_actions.length > 0 && (
                        <div className="border-t border-gray-700 pt-3">
                          <h5 className="text-xs font-semibold text-gray-400 mb-2">Recommended Actions</h5>
                          <ul className="space-y-1">
                            {alertExplanation.nurse_actions.map((action: string, idx: number) => (
                              <li key={idx} className="text-sm text-gray-300 flex items-start gap-2">
                                <CheckCircle2 className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                                {action}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">No alert explanation available</p>
                  )}
                </div>

                {/* Sepsis Bundle Timeline Panel */}
                <div>
                  <div className="flex items-center space-x-2 mb-3">
                    <Clock className="w-5 h-5 text-cyan-400" />
                    <h3 className="text-sm font-semibold text-white">Sepsis Bundle Timeline</h3>
                  </div>
                  
                  {loadingBundleTimeline ? (
                    <Skeleton className="h-40 w-full bg-gray-700 rounded-lg" />
                  ) : bundleTimeline && bundleTimeline.timeline ? (
                    <div className="bg-slate-900/70 border border-slate-600 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-4">
                        <div className="text-sm">
                          <span className="text-gray-400">Bundle Compliance:</span>
                          <span className={`ml-2 font-bold ${
                            bundleTimeline.summary?.compliance_percentage >= 80 ? 'text-green-400' :
                            bundleTimeline.summary?.compliance_percentage >= 50 ? 'text-amber-400' : 'text-red-400'
                          }`}>
                            {bundleTimeline.summary?.compliance_percentage?.toFixed(0) || 0}%
                          </span>
                        </div>
                        <div className="text-sm">
                          <span className="text-gray-400">Tasks:</span>
                          <span className="ml-2 font-bold text-white">
                            {bundleTimeline.summary?.completed || 0}/{bundleTimeline.summary?.total_tasks || 6}
                          </span>
                        </div>
                      </div>
                      
                      <div className="space-y-3">
                        {bundleTimeline.timeline.map((task: any) => {
                          const statusConfig: Record<string, { icon: any; color: string; bg: string }> = {
                            done: { icon: CheckCircle2, color: 'text-green-400', bg: 'bg-green-900/30 border-green-600/40' },
                            in_progress: { icon: Clock, color: 'text-blue-400', bg: 'bg-blue-900/30 border-blue-600/40' },
                            pending: { icon: Clock, color: 'text-amber-400', bg: 'bg-amber-900/30 border-amber-600/40' },
                            overdue: { icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-900/30 border-red-600/40' },
                            not_indicated: { icon: Activity, color: 'text-gray-400', bg: 'bg-gray-800/50 border-gray-600/40' },
                            ordered: { icon: Clock, color: 'text-purple-400', bg: 'bg-purple-900/30 border-purple-600/40' }
                          }
                          const config = statusConfig[task.status] || statusConfig.pending
                          const StatusIcon = config.icon
                          
                          return (
                            <div key={task.task_id} className={`rounded border p-3 ${config.bg}`}>
                              <div className="flex items-start justify-between">
                                <div className="flex items-start gap-3">
                                  <StatusIcon className={`w-5 h-5 mt-0.5 ${config.color}`} />
                                  <div>
                                    <div className="text-sm font-semibold text-white">{task.task_name}</div>
                                    <div className="text-xs text-gray-400">{task.description}</div>
                                    {task.completion_time && (
                                      <div className="text-xs text-gray-500 mt-1">
                                        Completed: {new Date(task.completion_time).toLocaleTimeString()}
                                      </div>
                                    )}
                                    {task.details && Object.keys(task.details).length > 0 && (
                                      <div className="text-xs text-gray-400 mt-1">
                                        {task.details.value && <span>Value: {task.details.value} | </span>}
                                        {task.details.result && <span>Result: {task.details.result} | </span>}
                                        {task.details.volume && <span>Volume: {task.details.volume} | </span>}
                                        {task.details.agent && <span>Agent: {task.details.agent}</span>}
                                      </div>
                                    )}
                                  </div>
                                </div>
                                <div className="text-right">
                                  <div className={`text-xs px-2 py-1 rounded ${config.bg} ${config.color}`}>
                                    {task.status.replace('_', ' ')}
                                  </div>
                                  <div className="text-xs text-gray-500 mt-1">
                                    Target: {task.target_time_minutes} min
                                  </div>
                                </div>
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">No bundle timeline available</p>
                  )}
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
                                    <span className="text-gray-400">Time to Stability (hours) - Inverted: Shorter = Better</span>
                                  </div>
                                  <div className="space-y-1">
                                    {(monteCarloPathways.top_3_pathways || []).map((pathway: any, idx: number) => {
                                      const maxTime = Math.max(...(monteCarloPathways.top_3_pathways || []).map((p: any) => p.expected_outcomes?.time_to_stability_hr?.mean || 0))
                                      const time = pathway.expected_outcomes?.time_to_stability_hr?.mean || 0
                                      const optimalTime = monteCarloPathways.top_3_pathways?.[0]?.expected_outcomes?.time_to_stability_hr?.mean || 0
                                      const timeDelta = idx > 0 ? (time - optimalTime).toFixed(1) : null
                                      const invertedPct = maxTime > 0 ? 100 - ((time / maxTime) * 100) : 0
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
                                              style={{ width: `${invertedPct}%` }}
                                            />
                                          </div>
                                          <div className="text-xs text-white w-16 text-right flex items-center justify-end space-x-1">
                                            <span>{time.toFixed(1)}h</span>
                                            {timeDelta && <span className="text-red-400 text-[10px]">+{timeDelta}h</span>}
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

                            <div className="space-y-2">
                              <div className="text-xs text-gray-500 italic">
                                Based on {monteCarloPathways.simulation_params?.samples_per_pathway || monteCarloPathways.top_3_pathways?.[0]?.samples || 100} Monte Carlo simulations per pathway
                              </div>
                              {monteCarloPathways.top_3_pathways?.[0] && (
                                <div className="p-3 bg-purple-950/30 border border-purple-600/40 rounded">
                                  <div className="text-xs text-purple-300 font-semibold mb-2">Composite Score Weighting</div>
                                  <div className="text-xs text-gray-300 space-y-1">
                                    <div>• Survival Probability: <span className="text-white font-semibold">60%</span> weight</div>
                                    <div>• Time to Stability: <span className="text-white font-semibold">25%</span> weight (inverted: faster = better)</div>
                                    <div>• Organ Preservation: <span className="text-white font-semibold">15%</span> weight</div>
                                  </div>
                                  <div className="text-xs text-gray-400 mt-2 italic">
                                    Optimal pathway selected based on highest composite score across all metrics
                                  </div>
                                </div>
                              )}
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

                {/* Comprehensive Clinical Data - 150+ Parameters */}
                <div className="border-t border-gray-700 pt-4">
                  <div className="flex items-center space-x-2 mb-3">
                    <Beaker className="w-5 h-5 text-emerald-400" />
                    <h3 className="text-sm font-semibold text-white">Comprehensive Clinical Data (150+ Parameters)</h3>
                  </div>
                  
                  {loadingComprehensive ? (
                    <div className="space-y-3">
                      <Skeleton className="h-10 w-full bg-gray-700 rounded-lg" />
                      <Skeleton className="h-40 w-full bg-gray-700 rounded-lg" />
                    </div>
                  ) : comprehensiveData ? (
                    <div className="bg-slate-900/70 border border-slate-600 rounded-lg p-4">
                      <div className="flex flex-wrap gap-2 mb-4">
                        {['vitals', 'cbc', 'metabolic', 'coagulation', 'abg', 'inflammatory', 'cardiac', 'renal', 'scores', 'microbiology', 'imaging', 'interventions'].map((cat) => (
                          <button
                            key={cat}
                            onClick={() => setActiveParamCategory(cat)}
                            className={`px-3 py-1 text-xs rounded-full transition-colors ${
                              activeParamCategory === cat
                                ? 'bg-emerald-600 text-white'
                                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                            }`}
                          >
                            {cat.charAt(0).toUpperCase() + cat.slice(1)}
                          </button>
                        ))}
                      </div>
                      
                      <div className="max-h-64 overflow-y-auto">
                        {comprehensiveData.current_parameters && comprehensiveData.current_parameters[activeParamCategory] ? (
                          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                            {Object.entries(comprehensiveData.current_parameters[activeParamCategory]).map(([key, value]: [string, any]) => (
                              <div key={key} className="p-2 bg-gray-800/50 rounded border border-gray-700">
                                <div className="text-xs text-gray-400 truncate">{key.replace(/_/g, ' ')}</div>
                                <div className="text-sm font-semibold text-white">
                                  {typeof value === 'number' ? value.toFixed(2) : String(value)}
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-xs text-gray-400 text-center py-4">
                            No data available for {activeParamCategory}
                          </div>
                        )}
                      </div>
                      
                      {comprehensiveData.archetype && (
                        <div className="mt-4 p-3 bg-purple-950/30 border border-purple-600/40 rounded">
                          <div className="text-xs text-purple-300 font-semibold mb-1">Patient Archetype</div>
                          <div className="text-sm text-white">{comprehensiveData.archetype.replace(/_/g, ' ')}</div>
                          {comprehensiveData.archetype_description && (
                            <div className="text-xs text-gray-300 mt-1">{comprehensiveData.archetype_description}</div>
                          )}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-xs text-gray-400 text-center py-4">
                      No comprehensive data available
                    </div>
                  )}
                </div>

                {/* Multi-Agent Analysis Results */}
                <div className="border-t border-gray-700 pt-4">
                  <div className="flex items-center space-x-2 mb-3">
                    <Brain className="w-5 h-5 text-cyan-400" />
                    <h3 className="text-sm font-semibold text-white">Multi-Agent Deep Analysis</h3>
                  </div>
                  
                  {loadingMultiAgent ? (
                    <div className="space-y-3">
                      <Skeleton className="h-20 w-full bg-gray-700 rounded-lg" />
                      <Skeleton className="h-20 w-full bg-gray-700 rounded-lg" />
                    </div>
                  ) : multiAgentAnalysis ? (
                    <div className="bg-slate-900/70 border border-slate-600 rounded-lg p-4 space-y-4">
                      {/* Overall Assessment */}
                      <div className="p-3 bg-gray-800/50 rounded border border-gray-700">
                        <div className="text-xs text-gray-400 mb-1">Overall Assessment</div>
                        <div className="text-sm text-white">{multiAgentAnalysis.overall_assessment}</div>
                      </div>
                      
                      {/* Key Metrics */}
                      <div className="grid grid-cols-3 gap-3">
                        <div className="p-2 bg-gray-800/50 rounded border border-gray-700 text-center">
                          <div className="text-xs text-gray-400">Sepsis Trajectory</div>
                          <div className={`text-sm font-bold ${
                            multiAgentAnalysis.sepsis_trajectory === 'worsening' ? 'text-red-400' :
                            multiAgentAnalysis.sepsis_trajectory === 'improving' ? 'text-green-400' : 'text-yellow-400'
                          }`}>
                            {multiAgentAnalysis.sepsis_trajectory}
                          </div>
                        </div>
                        <div className="p-2 bg-gray-800/50 rounded border border-gray-700 text-center">
                          <div className="text-xs text-gray-400">Mortality Risk</div>
                          <div className={`text-sm font-bold ${
                            multiAgentAnalysis.mortality_risk === 'very_high' || multiAgentAnalysis.mortality_risk === 'high' ? 'text-red-400' :
                            multiAgentAnalysis.mortality_risk === 'moderate' ? 'text-yellow-400' : 'text-green-400'
                          }`}>
                            {multiAgentAnalysis.mortality_risk?.replace(/_/g, ' ')}
                          </div>
                        </div>
                        <div className="p-2 bg-gray-800/50 rounded border border-gray-700 text-center">
                          <div className="text-xs text-gray-400">Confidence</div>
                          <div className="text-sm font-bold text-cyan-400">
                            {Math.round((multiAgentAnalysis.confidence_score || 0) * 100)}%
                          </div>
                        </div>
                      </div>
                      
                      {/* Primary Concerns */}
                      {multiAgentAnalysis.primary_concerns && multiAgentAnalysis.primary_concerns.length > 0 && (
                        <div>
                          <div className="text-xs text-gray-400 mb-2">Primary Concerns</div>
                          <div className="space-y-1">
                            {multiAgentAnalysis.primary_concerns.map((concern: string, idx: number) => (
                              <div key={idx} className="text-xs text-red-300 flex items-start">
                                <span className="mr-2">•</span>
                                <span>{concern}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {/* Agent Findings */}
                      {multiAgentAnalysis.agent_findings && multiAgentAnalysis.agent_findings.length > 0 && (
                        <div>
                          <div className="text-xs text-gray-400 mb-2">Specialized Agent Findings</div>
                          <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                            {multiAgentAnalysis.agent_findings.map((finding: any, idx: number) => (
                              <div key={idx} className={`p-2 rounded border ${
                                finding.overall_risk === 'critical' ? 'bg-red-950/30 border-red-600/40' :
                                finding.overall_risk === 'high' ? 'bg-orange-950/30 border-orange-600/40' :
                                finding.overall_risk === 'moderate' ? 'bg-yellow-950/30 border-yellow-600/40' :
                                'bg-green-950/30 border-green-600/40'
                              }`}>
                                <div className="flex items-center justify-between mb-1">
                                  <div className="text-xs font-semibold text-white">{finding.agent_name}</div>
                                  <div className={`text-xs px-1.5 py-0.5 rounded ${
                                    finding.overall_risk === 'critical' ? 'bg-red-600 text-white' :
                                    finding.overall_risk === 'high' ? 'bg-orange-600 text-white' :
                                    finding.overall_risk === 'moderate' ? 'bg-yellow-600 text-black' :
                                    'bg-green-600 text-white'
                                  }`}>
                                    {finding.overall_risk}
                                  </div>
                                </div>
                                <div className="text-xs text-gray-300 line-clamp-2">{finding.summary}</div>
                                {finding.confidence && (
                                  <div className="text-xs text-gray-500 mt-1">Confidence: {Math.round(finding.confidence * 100)}%</div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {/* Cross-System Correlations */}
                      {multiAgentAnalysis.cross_system_correlations && multiAgentAnalysis.cross_system_correlations.length > 0 && (
                        <div>
                          <div className="text-xs text-gray-400 mb-2">Cross-System Correlations</div>
                          <div className="space-y-2">
                            {multiAgentAnalysis.cross_system_correlations.map((corr: any, idx: number) => (
                              <div key={idx} className="p-2 bg-purple-950/30 border border-purple-600/40 rounded">
                                <div className="flex items-center justify-between mb-1">
                                  <div className="text-xs font-semibold text-purple-300">{corr.pattern_name}</div>
                                  <div className={`text-xs px-1.5 py-0.5 rounded ${
                                    corr.severity === 'critical' ? 'bg-red-600 text-white' :
                                    corr.severity === 'high' ? 'bg-orange-600 text-white' : 'bg-yellow-600 text-black'
                                  }`}>
                                    {corr.severity}
                                  </div>
                                </div>
                                <div className="text-xs text-gray-300">{corr.clinical_interpretation}</div>
                                {corr.involved_systems && (
                                  <div className="text-xs text-gray-500 mt-1">
                                    Systems: {corr.involved_systems.join(', ')}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {/* Recommended Actions */}
                      {multiAgentAnalysis.recommended_actions && multiAgentAnalysis.recommended_actions.length > 0 && (
                        <div>
                          <div className="text-xs text-gray-400 mb-2">Recommended Actions</div>
                          <div className="space-y-1">
                            {multiAgentAnalysis.recommended_actions.map((action: string, idx: number) => (
                              <div key={idx} className="text-xs text-emerald-300 flex items-start">
                                <span className="mr-2">{idx + 1}.</span>
                                <span>{action}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-xs text-gray-400 text-center py-4">
                      No multi-agent analysis available
                    </div>
                  )}
                </div>

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
