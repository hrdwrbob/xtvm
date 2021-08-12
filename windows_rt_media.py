import asyncio

from winrt.windows.media.control import \
    GlobalSystemMediaTransportControlsSessionManager as MediaManager
import winrt.windows.media.control
import winrt.windows.foundation
#import winrt.windows.applicationmodel
#from  winrt.windows.applicationmodel import AppInfo




class WindowsRuntimeMedia():
  def __init__(self):
    session = asyncio.run(winrtmedia.get_current_session())
    self._sourcename = session.source_app_user_model_id
    self._session = session
  
  def next_source(self):
    sessions = asyncio.run(winrtmedia.get_sessions())
    current_name = self._sourcename
    self._sourcename = None
    for index,session in enumerate(sessions):
      if (session.source_app_user_model_id == current_name):
        if index+1 == len(sessions):
          self._sourcename = sessions[0].source_app_user_model_id
          self._session = sessions[0]
        else:
          self._sourcename = sessions[index+1].source_app_user_model_id
          self._session = sessions[index+1]
    #fallback if we didn't find the session.
    if self._sourcename == None:
      self._sourcename = sessions[0].source_app_user_model_id
      self._session = sessions[0]
    return self._sourcename

      
    
  def prev_source(self):  
    sessions = asyncio.run(winrtmedia.get_sessions())
    current_name = self._sourcename
    self._sourcename = None
    for index,session in enumerate(sessions):
      if (session.source_app_user_model_id == current_name):
        if index == 0:
          self._sourcename = sessions[len(sessions)-1].source_app_user_model_id
          self._session = sessions[len(sessions)-1]
        else:
          self._sourcename = sessions[index-1].source_app_user_model_id
          self._session = sessions[index-1]
    #fallback if we didn't find the session.
    if self._sourcename == None:
      self._sourcename = sessions[0].source_app_user_model_id
      self._session = sessions[0]
    return self._sourcename
    
  def jog_backward(self):
    return asyncio.run(winrtmedia.jog_backward(self._session))
  def jog_forward(self):
    return asyncio.run(winrtmedia.jog_forward(self._session))
  def playpause(self):
    return asyncio.run(winrtmedia.playpause(self._session))
  def prev(self):
    return asyncio.run(winrtmedia.prev(self._session))
  def next(self):
    return asyncio.run(winrtmedia.next(self._session))
  def stop(self):
    return asyncio.run(winrtmedia.stop(self._session))
  
  def get_source_name(self):
    return self._sourcename
    
  async def get_track_name(self):
    info = await winrtmedia.get_session_info(self._session)
    return info['title']

class winrtmedia():
  @staticmethod
  async def get_sessions():
      sessions = await MediaManager.request_async()
      return sessions.get_sessions()
 
  @staticmethod
  async def get_current_session():
      sessions = await MediaManager.request_async()
      return sessions.get_current_session()
      
      
      
  @staticmethod
  async def get_session_info(session):
    info = await session.try_get_media_properties_async()

    # song_attr[0] != '_' ignores system attributes
    info_dict = {song_attr: info.__getattribute__(song_attr) for song_attr in dir(info) if song_attr[0] != '_'}

    # converts winrt vector to list
    info_dict['genres'] = list(info_dict['genres'])

    return info_dict

  @staticmethod
  async def pause(session):
    await session.try_pause_async()

  @staticmethod
  async def play(session):
    await session.try_play_async()

  @staticmethod
  async def playpause(session):
    await session.try_toggle_play_pause_async()

  @staticmethod
  async def jog_forward(session):
    timeline = session.get_timeline_properties()
    #TryChangePlaybackPositionAsync
    ticks = 5 * 10000000
    skipto = timeline.position.duration + ticks
    await session.try_change_playback_position_async(skipto)

  @staticmethod
  async def jog_backward(session):
    timeline = session.get_timeline_properties()
    #TryChangePlaybackPositionAsync
    ticks = 5 * 10000000
    skipto = timeline.position.duration - ticks
    await session.try_change_playback_position_async(skipto)
    
  @staticmethod
  async def stop(session):
    await session.try_stop_async()

  @staticmethod
  async def next(session):
    await session.try_skip_next_async()

  @staticmethod
  async def prev(session):
    await session.try_skip_previous_async()