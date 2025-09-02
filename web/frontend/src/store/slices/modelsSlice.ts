import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import axios from 'axios'
import { Model } from '../../types'

interface ModelsState {
  models: Model[]
  loading: boolean
  error: string | null
}

const initialState: ModelsState = {
  models: [],
  loading: false,
  error: null,
}

export const fetchModels = createAsyncThunk(
  'models/fetchModels',
  async () => {
    const response = await axios.get('/api/models/')
    return response.data
  }
)

const modelsSlice = createSlice({
  name: 'models',
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchModels.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchModels.fulfilled, (state, action) => {
        state.loading = false
        state.models = action.payload
      })
      .addCase(fetchModels.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || 'Failed to fetch models'
      })
  },
})

export default modelsSlice.reducer