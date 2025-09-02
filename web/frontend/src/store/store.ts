import { configureStore } from '@reduxjs/toolkit'
import testsReducer from './slices/testsSlice'
import sessionsReducer from './slices/sessionsSlice'

export const store = configureStore({
  reducer: {
    tests: testsReducer,
    sessions: sessionsReducer,
  },
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch