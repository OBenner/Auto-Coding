/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { useDownloadStore } from '../download-store';

describe('download-store', () => {
  beforeEach(() => {
    useDownloadStore.setState({ downloads: {} });
  });

  describe('startDownload', () => {
    it('should create a new download entry', () => {
      useDownloadStore.getState().startDownload('gpt-4');
      const download = useDownloadStore.getState().downloads['gpt-4'];
      expect(download).toBeDefined();
      expect(download.modelName).toBe('gpt-4');
      expect(download.status).toBe('starting');
      expect(download.percentage).toBe(0);
    });

    it('should handle multiple downloads', () => {
      useDownloadStore.getState().startDownload('model-a');
      useDownloadStore.getState().startDownload('model-b');
      expect(Object.keys(useDownloadStore.getState().downloads)).toHaveLength(2);
    });
  });

  describe('updateProgress', () => {
    it('should update download progress', () => {
      useDownloadStore.getState().startDownload('model-a');
      useDownloadStore.getState().updateProgress('model-a', { percentage: 50 });
      const download = useDownloadStore.getState().downloads['model-a'];
      expect(download.percentage).toBe(50);
      expect(download.status).toBe('downloading');
    });

    it('should keep starting status when percentage is 0', () => {
      useDownloadStore.getState().startDownload('model-a');
      useDownloadStore.getState().updateProgress('model-a', { percentage: 0 });
      expect(useDownloadStore.getState().downloads['model-a'].status).toBe('starting');
    });

    it('should update speed and time remaining', () => {
      useDownloadStore.getState().startDownload('model-a');
      useDownloadStore.getState().updateProgress('model-a', {
        percentage: 50,
        speed: '5.2 MB/s',
        timeRemaining: '2m remaining',
      });
      const download = useDownloadStore.getState().downloads['model-a'];
      expect(download.speed).toBe('5.2 MB/s');
      expect(download.timeRemaining).toBe('2m remaining');
    });

    it('should not update non-existent download', () => {
      useDownloadStore.getState().updateProgress('nonexistent', { percentage: 50 });
      expect(useDownloadStore.getState().downloads['nonexistent']).toBeUndefined();
    });
  });

  describe('completeDownload', () => {
    it('should mark download as completed at 100%', () => {
      useDownloadStore.getState().startDownload('model-a');
      useDownloadStore.getState().completeDownload('model-a');
      const download = useDownloadStore.getState().downloads['model-a'];
      expect(download.status).toBe('completed');
      expect(download.percentage).toBe(100);
    });

    it('should not affect non-existent download', () => {
      useDownloadStore.getState().completeDownload('nonexistent');
      expect(useDownloadStore.getState().downloads['nonexistent']).toBeUndefined();
    });
  });

  describe('failDownload', () => {
    it('should mark download as failed with error', () => {
      useDownloadStore.getState().startDownload('model-a');
      useDownloadStore.getState().failDownload('model-a', 'Network error');
      const download = useDownloadStore.getState().downloads['model-a'];
      expect(download.status).toBe('failed');
      expect(download.error).toBe('Network error');
    });
  });

  describe('clearDownload', () => {
    it('should remove download entry', () => {
      useDownloadStore.getState().startDownload('model-a');
      useDownloadStore.getState().startDownload('model-b');
      useDownloadStore.getState().clearDownload('model-a');
      expect(useDownloadStore.getState().downloads['model-a']).toBeUndefined();
      expect(useDownloadStore.getState().downloads['model-b']).toBeDefined();
    });
  });

  describe('selectors', () => {
    it('hasActiveDownloads should return false when no downloads', () => {
      expect(useDownloadStore.getState().hasActiveDownloads()).toBe(false);
    });

    it('hasActiveDownloads should return true for starting downloads', () => {
      useDownloadStore.getState().startDownload('model-a');
      expect(useDownloadStore.getState().hasActiveDownloads()).toBe(true);
    });

    it('hasActiveDownloads should return true for downloading', () => {
      useDownloadStore.getState().startDownload('model-a');
      useDownloadStore.getState().updateProgress('model-a', { percentage: 50 });
      expect(useDownloadStore.getState().hasActiveDownloads()).toBe(true);
    });

    it('hasActiveDownloads should return false for completed downloads only', () => {
      useDownloadStore.getState().startDownload('model-a');
      useDownloadStore.getState().completeDownload('model-a');
      expect(useDownloadStore.getState().hasActiveDownloads()).toBe(false);
    });

    it('hasActiveDownloads should return false for failed downloads only', () => {
      useDownloadStore.getState().startDownload('model-a');
      useDownloadStore.getState().failDownload('model-a', 'err');
      expect(useDownloadStore.getState().hasActiveDownloads()).toBe(false);
    });

    it('getActiveDownloads should return only active downloads', () => {
      useDownloadStore.getState().startDownload('model-a');
      useDownloadStore.getState().startDownload('model-b');
      useDownloadStore.getState().completeDownload('model-b');
      const active = useDownloadStore.getState().getActiveDownloads();
      expect(active).toHaveLength(1);
      expect(active[0].modelName).toBe('model-a');
    });
  });

  describe('full download lifecycle', () => {
    it('should track complete download flow', () => {
      const store = useDownloadStore.getState();
      store.startDownload('model-x');
      expect(store.hasActiveDownloads()).toBe(true);

      useDownloadStore.getState().updateProgress('model-x', { percentage: 25 });
      expect(useDownloadStore.getState().downloads['model-x'].status).toBe('downloading');

      useDownloadStore.getState().updateProgress('model-x', { percentage: 75 });
      expect(useDownloadStore.getState().downloads['model-x'].percentage).toBe(75);

      useDownloadStore.getState().completeDownload('model-x');
      expect(useDownloadStore.getState().downloads['model-x'].status).toBe('completed');
      expect(useDownloadStore.getState().hasActiveDownloads()).toBe(false);
    });
  });
});
