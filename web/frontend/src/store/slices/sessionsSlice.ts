import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import axios from 'axios'
import { Session } from '../../types'

export const fetchModelsForProvider = createAsyncThunk(
  'models/fetchModelsForProvider',
  async (provider: string) => {
    const response = await axios.get(`/api/models/history/${provider}`)
    return { provider, models: response.data }
  }
)

export const saveModel = createAsyncThunk(
  'models/saveModel',
  async ({ provider, modelName }: { provider: string; modelName: string }) => {
    await axios.post(`/api/models/history/${provider}/${modelName}`)
    return { provider, modelName }
  }
)

interface SessionsState {
  sessions: Session[]
  currentSession: Session | null
  loading: boolean
  error: string | null
  savedModels: { [provider: string]: string[] }
  modelsLoading: boolean
}

const initialState: SessionsState = {
  sessions: [],
  currentSession: null,
  loading: false,
  error: null,
  savedModels: {},
  modelsLoading: false,
}

export const fetchSessions = createAsyncThunk(
  'sessions/fetchSessions',
  async () => {
    const response = await axios.get('/api/sessions/')
    return response.data
  }
)

export const createSession = createAsyncThunk(
  'sessions/createSession',
  async (sessionData: any) => {
    const response = await axios.post('/api/sessions/', sessionData)
    return response.data
  }
)

export const startSession = createAsyncThunk(
  'sessions/startSession',
  async (sessionId: string) => {
    const response = await axios.post(`/api/sessions/${sessionId}/start`)
    return response.data
  }
)

const sessionsSlice = createSlice({
  name: 'sessions',
  initialState,
  reducers: {
    setCurrentSession: (state, action) => {
      state.currentSession = action.payload
    },
    updateSessionLogs: (state, action) => {
      if (state.currentSession) {
        state.currentSession.logs = action.payload
      }
    },
    updateSessionProgress: (state, action) => {
      if (state.currentSession) {
        state.currentSession.progress = action.payload.progress
        state.currentSession.current_test = action.payload.current_test
        state.currentSession.status = action.payload.status
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Existing reducers...
      .addCase(fetchSessions.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchSessions.fulfilled, (state, action) => {
        state.loading = false
        state.sessions = action.payload
      })
      .addCase(fetchSessions.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || 'Failed to fetch sessions'
      })
      .addCase(createSession.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(createSession.fulfilled, (state, action) => {
        state.loading = false
        state.currentSession = action.payload
        state.sessions.push(action.payload)
        console.log('Redux: createSession.fulfilled - currentSession set to:', action.payload)
      })
      .addCase(createSession.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || 'Failed to create session'
      })
      .addCase(startSession.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(startSession.fulfilled, (state, action) => {
        state.loading = false
        if (state.currentSession) {
          state.currentSession = action.payload
          console.log('Redux: startSession.fulfilled - currentSession updated to:', action.payload)
        } else {
          console.log('Redux: startSession.fulfilled - no currentSession to update')
        }
      })
      .addCase(startSession.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || 'Failed to start session'
      })
      // New model history reducers
      .addCase(fetchModelsForProvider.pending, (state) => {
        state.modelsLoading = true
      })
      .addCase(fetchModelsForProvider.fulfilled, (state, action) => {
        state.modelsLoading = false
        state.savedModels[action.payload.provider] = action.payload.models
      })
      .addCase(fetchModelsForProvider.rejected, (state) => {
        state.modelsLoading = false
      })
      .addCase(saveModel.fulfilled, (state, action) => {
        const { provider, modelName } = action.payload
        if (!state.savedModels[provider]) {
          state.savedModels[provider] = []
        }
        // Remove if exists and add to beginning
        const models = state.savedModels[provider].filter(m => m !== modelName)
        models.unshift(modelName)
        state.savedModels[provider] = models.slice(0, 10) // Keep only 10 most recent
      })
  },
})

export const { setCurrentSession, updateSessionLogs, updateSessionProgress } = sessionsSlice.actions
export default sessionsSlice.reducer