import { configureStore } from '@reduxjs/toolkit'
import testsReducer from './slices/testsSlice'
import sessionsReducer from './slices/sessionsSlice'
import modelsReducer from './slices/modelsSlice'

export const store = configureStore({
  reducer: {
    tests: testsReducer,
    sessions: sessionsReducer,
    models: modelsReducer,
  },
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch

// Export the store itself for use in components
export default store