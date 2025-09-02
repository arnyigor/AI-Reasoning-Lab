import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import axios from 'axios'
import { Test } from '../../types'

interface TestsState {
  tests: Record<string, Test>
  loading: boolean
  error: string | null
}

const initialState: TestsState = {
  tests: {},
  loading: false,
  error: null,
}

export const fetchTests = createAsyncThunk(
  'tests/fetchTests',
  async () => {
    const response = await axios.get('/api/tests/')
    return response.data
  }
)

const testsSlice = createSlice({
  name: 'tests',
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchTests.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchTests.fulfilled, (state, action) => {
        state.loading = false
        state.tests = action.payload
      })
      .addCase(fetchTests.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || 'Failed to fetch tests'
      })
  },
})

export default testsSlice.reducer