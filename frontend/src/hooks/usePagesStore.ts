import { useEffect, useRef, useState } from 'react'
import { listPages } from '../api'
import type { GeneratedPage, PageListData } from '../api'

export function usePagesStore() {
  const [pages, setPages] = useState<GeneratedPage[]>([])
  const [isPageListBootstrapped, setIsPageListBootstrapped] = useState(false)
  const [isPageListRefreshing, setIsPageListRefreshing] = useState(false)
  const initialRequestKeyRef = useRef<string | null>(null)
  const initialRequestPromiseRef = useRef<Promise<PageListData> | null>(null)
  const [pageListData, setPageListData] = useState<PageListData>({
    list: [],
    pageNo: 1,
    pageSize: 10,
    total: 0,
  })

  const isPageListLoading = !isPageListBootstrapped || isPageListRefreshing

  const refreshPages = async (pageNo = pageListData.pageNo, pageSize = pageListData.pageSize) => {
    setIsPageListRefreshing(true)
    try {
      const result = await listPages(pageNo, pageSize)
      setPages(result.list)
      setPageListData(result)
    } finally {
      setIsPageListRefreshing(false)
    }
  }

  useEffect(() => {
    let cancelled = false
    const requestKey = `${pageListData.pageNo}-${pageListData.pageSize}`
    let requestPromise: Promise<PageListData>

    if (!isPageListBootstrapped && initialRequestKeyRef.current === requestKey && initialRequestPromiseRef.current) {
      requestPromise = initialRequestPromiseRef.current
    } else {
      initialRequestKeyRef.current = requestKey
      requestPromise = listPages(pageListData.pageNo, pageListData.pageSize)
      if (!isPageListBootstrapped) {
        initialRequestPromiseRef.current = requestPromise
      }
    }

    void requestPromise
      .then((result) => {
        if (!cancelled) {
          setPages(result.list)
          setPageListData(result)
          setIsPageListBootstrapped(true)
          initialRequestPromiseRef.current = null
        }
      })
      .catch(() => {
        if (!cancelled) {
          setPages([])
          setPageListData({
            list: [],
            pageNo: 1,
            pageSize: 10,
            total: 0,
          })
          setIsPageListBootstrapped(true)
          initialRequestPromiseRef.current = null
        }
      })

    return () => {
      cancelled = true
    }
  }, [isPageListBootstrapped, pageListData.pageNo, pageListData.pageSize])

  return {
    isPageListLoading,
    pageListData,
    pages,
    refreshPages,
  }
}
