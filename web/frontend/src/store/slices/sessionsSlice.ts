import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import axios from 'axios'
import { Session } from '../../types'

interface SessionsState {
  sessions: Session[]
  currentSession: Session | null
  loading: boolean
  error: string | null
}

const initialState: SessionsState = {
  sessions: [],
  currentSession: null,
  loading: false,
  error: null,
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
  async (sessionData: { test_ids: string[], model_configuration: any, session_name?: string }) => {
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
  },
  extraReducers: (builder) => {
    builder
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
        }
      })
      .addCase(startSession.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || 'Failed to start session'
      })
  },
})

export const { setCurrentSession } = sessionsSlice.actions
export default sessionsSlice.reducer