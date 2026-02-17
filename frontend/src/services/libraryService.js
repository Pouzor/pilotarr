import pilotarrClient from "../lib/pilotarrClient";

/**
 * Get recent items (media and request) from dashboard API
 * @param {number} limit - Number of items to fetch
 * @param {string} sortBy - Sort field (added_date, ratio, size, title)
 * @param {string} sortOrder - Sort order (asc, desc)
 * @returns {Promise<Array>} Array of recent items
 */
export const getRecentItems = async (
  limit = 10,
  sortBy = "added_date",
  sortOrder = "desc",
) => {
  try {
    const response = await pilotarrClient?.get(
      `/dashboard/recent-items?limit=${limit}&sort_by=${sortBy}&sort_order=${sortOrder}`,
    );
    return response?.data || [];
  } catch (error) {
    console.error("Error fetching recent items:", error?.message);
    return [];
  }
};

/**
 * Get all library items
 * @param {number} limit - Number of items to fetch
 * @param {string} sortBy - Sort field (added_date, ratio, size, title)
 * @param {string} sortOrder - Sort order (asc, desc)
 * @returns {Promise<Array>} Array item
 */
export const getLibraryItems = async (
  limit = 20,
  sortBy = "added_date",
  sortOrder = "desc",
) => {
  try {
    const response = await pilotarrClient?.get(
      `/library?limit=${limit}&sort_by=${sortBy}&sort_order=${sortOrder}`,
    );
    return response?.data || [];
  } catch (error) {
    console.error("Error fetching library items:", error?.message);
    return [];
  }
};

/**
 * Get library item by id
 * @param {string} id - Media item ID
 * @returns {Promise<Object|null>} Media detail object or null
 */
export const getLibraryItemById = async (id) => {
  try {
    const response = await pilotarrClient?.get(`/library/${id}`);
    return response?.data || [];
  } catch (error) {
    console.error("Error fetching library items:", error?.message);
    return null;
  }
};

/**
 * Get all seasons with embedded episodes for a TV show (single request)
 * @param {string} id - Library item ID
 * @returns {Promise<Array>} Array of seasons with episodes
 */
export const getSeasonsWithEpisodes = async (id) => {
  try {
    const response = await pilotarrClient?.get(
      `/library/${id}/seasons-with-episodes`,
    );
    return response?.data || [];
  } catch (error) {
    console.error("Error fetching seasons with episodes:", error?.message);
    return [];
  }
};

/**
 * Get detailed information for a specific media item
 * @param {string} id - Media item ID
 * @returns {Promise<Object|null>} Media detail object or null
 */
export const getMediaDetail = async (id) => {
  // Mock data for demonstration
  const mockMovies = {
    1: {
      id: "1",
      title: "The Shawshank Redemption",
      year: 1994,
      mediaType: "movie",
      image:
        "https://img.rocket.new/generatedImages/rocket_gen_img_1e7c1ee7d-1766845815525.png",
      imageAlt: "The Shawshank Redemption movie poster showing Andy Dufresne",
      backdropImage:
        "https://img.rocket.new/generatedImages/rocket_gen_img_1d395bfc4-1764681696426.png",
      quality: "Bluray-1080p",
      rating: 9.3,
      description:
        "Two imprisoned men bond over a number of years, finding solace and eventual redemption through acts of common decency.",
      releaseDate: "1994-09-23",
      status: "Released",
      network: null,
      runtime: 142,
      genres: ["Drama", "Crime"],
      cast: ["Tim Robbins", "Morgan Freeman", "Bob Gunton", "William Sadler"],
      path: "/movies/The Shawshank Redemption (1994)",
      qualityProfile: "HD-1080p",
      monitored: true,
      size: "8.5 GB",
      nbMedia: 1,
      viewCount: 156,
      playbackProgress: 0,
      subtitles: [
        { language: "English", format: "SRT" },
        { language: "French", format: "SRT" },
        { language: "Spanish", format: "SRT" },
      ],

      torrentInfo: {
        hash: "a1b2c3d4e5f6g7h8i9j0",
        name: "The.Shawshank.Redemption.1994.1080p.BluRay.x264",
        status: "seeding",
        ratio: 3.45,
        seedingTime: 2592000,
        progress: 100,
        size: "8.5 GB",
      },
      seasons: [],
    },
    2: {
      id: "2",
      title: "Inception",
      year: 2010,
      mediaType: "movie",
      image:
        "https://img.rocket.new/generatedImages/rocket_gen_img_1dbfd00a0-1764665583149.png",
      imageAlt: "Inception movie poster featuring Leonardo DiCaprio",
      backdropImage:
        "https://images.unsplash.com/photo-1705948353989-ecb64769f1ef",
      quality: "Bluray-2160p",
      rating: 8.8,
      description:
        "A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O.",
      releaseDate: "2010-07-16",
      status: "Released",
      network: null,
      runtime: 148,
      genres: ["Action", "Science Fiction", "Adventure"],
      cast: [
        "Leonardo DiCaprio",
        "Joseph Gordon-Levitt",
        "Ellen Page",
        "Tom Hardy",
      ],
      path: "/movies/Inception (2010)",
      qualityProfile: "Ultra-HD",
      monitored: true,
      size: "15.2 GB",
      nbMedia: 1,
      viewCount: 203,
      playbackProgress: 45,
      subtitles: [
        { language: "English", format: "SRT" },
        { language: "French", format: "ASS" },
      ],

      torrentInfo: {
        hash: "b2c3d4e5f6g7h8i9j0k1",
        name: "Inception.2010.2160p.BluRay.x265",
        status: "seeding",
        ratio: 5.67,
        seedingTime: 5184000,
        progress: 100,
        size: "15.2 GB",
      },
      seasons: [],
    },
  };

  const mockTVShows = {
    3: {
      id: "3",
      title: "Breaking Bad",
      year: 2008,
      mediaType: "tv",
      image:
        "https://img.rocket.new/generatedImages/rocket_gen_img_132f74d43-1767463020900.png",
      imageAlt: "Breaking Bad TV show poster featuring Walter White",
      backdropImage:
        "https://img.rocket.new/generatedImages/rocket_gen_img_17a893cc4-1767879469489.png",
      quality: "Bluray-1080p",
      rating: 9.5,
      description:
        "A high school chemistry teacher diagnosed with inoperable lung cancer turns to manufacturing and selling methamphetamine in order to secure his family's future.",
      releaseDate: "2008-01-20",
      status: "Ended",
      network: "AMC",
      runtime: 47,
      genres: ["Drama", "Crime", "Thriller"],
      cast: ["Bryan Cranston", "Aaron Paul", "Anna Gunn", "Dean Norris"],
      path: "/tv/Breaking Bad",
      qualityProfile: "HD-1080p",
      monitored: true,
      size: "142.8 GB",
      nbMedia: 62,
      viewCount: 1247,
      playbackProgress: 0,
      subtitles: [
        { language: "English", format: "SRT" },
        { language: "Spanish", format: "SRT" },
      ],

      torrentInfo: {
        hash: "c3d4e5f6g7h8i9j0k1l2",
        name: "Breaking.Bad.Complete.Series.1080p.BluRay",
        status: "seeding",
        ratio: 8.92,
        seedingTime: 15552000,
        progress: 100,
        size: "142.8 GB",
      },
      seasons: [
        {
          seasonNumber: 1,
          name: "Season 1",
          episodes: [
            {
              episodeNumber: 1,
              title: "Pilot",
              airDate: "2008-01-20",
              downloadStatus: "downloaded",
              hasSubtitles: true,
              subtitleLanguages: ["English", "Spanish"],
              fileSize: "2.1 GB",
              watched: true,
              monitored: true,
            },
            {
              episodeNumber: 2,
              title: "Cat's in the Bag...",
              airDate: "2008-01-27",
              downloadStatus: "downloaded",
              hasSubtitles: true,
              subtitleLanguages: ["English", "Spanish"],
              fileSize: "2.0 GB",
              watched: true,
              monitored: true,
            },
            {
              episodeNumber: 3,
              title: "...And the Bag's in the River",
              airDate: "2008-02-10",
              downloadStatus: "downloaded",
              hasSubtitles: true,
              subtitleLanguages: ["English"],
              fileSize: "2.1 GB",
              watched: false,
              monitored: true,
            },
          ],
        },
        {
          seasonNumber: 2,
          name: "Season 2",
          episodes: [
            {
              episodeNumber: 1,
              title: "Seven Thirty-Seven",
              airDate: "2009-03-08",
              downloadStatus: "downloaded",
              hasSubtitles: true,
              subtitleLanguages: ["English", "Spanish"],
              fileSize: "2.2 GB",
              watched: false,
              monitored: true,
            },
            {
              episodeNumber: 2,
              title: "Grilled",
              airDate: "2009-03-15",
              downloadStatus: "missing",
              hasSubtitles: false,
              subtitleLanguages: [],
              fileSize: null,
              watched: false,
              monitored: true,
            },
          ],
        },
      ],
    },
    4: {
      id: "4",
      title: "Stranger Things",
      year: 2016,
      mediaType: "tv",
      image:
        "https://img.rocket.new/generatedImages/rocket_gen_img_18fc9d2c2-1770494626079.png",
      imageAlt: "Stranger Things TV show poster with main cast",
      backdropImage:
        "https://img.rocket.new/generatedImages/rocket_gen_img_1492b7b67-1767527751487.png",
      quality: "WEB-DL-2160p",
      rating: 8.7,
      description:
        "When a young boy vanishes, a small town uncovers a mystery involving secret experiments, terrifying supernatural forces, and one strange little girl.",
      releaseDate: "2016-07-15",
      status: "Continuing",
      network: "Netflix",
      runtime: 51,
      genres: ["Sci-Fi & Fantasy", "Mystery", "Drama"],
      cast: [
        "Millie Bobby Brown",
        "Finn Wolfhard",
        "Winona Ryder",
        "David Harbour",
      ],
      path: "/tv/Stranger Things",
      qualityProfile: "Ultra-HD",
      monitored: true,
      size: "98.4 GB",
      nbMedia: 34,
      viewCount: 892,
      playbackProgress: 67,
      subtitles: [
        { language: "English", format: "SRT" },
        { language: "French", format: "SRT" },
        { language: "German", format: "SRT" },
      ],

      torrentInfo: {
        hash: "d4e5f6g7h8i9j0k1l2m3",
        name: "Stranger.Things.S01-S04.2160p.WEB-DL",
        status: "seeding",
        ratio: 4.23,
        seedingTime: 8640000,
        progress: 100,
        size: "98.4 GB",
      },
      seasons: [
        {
          seasonNumber: 1,
          name: "Season 1",
          episodes: [
            {
              episodeNumber: 1,
              title: "Chapter One: The Vanishing of Will Byers",
              airDate: "2016-07-15",
              downloadStatus: "downloaded",
              hasSubtitles: true,
              subtitleLanguages: ["English", "French", "German"],
              fileSize: "3.2 GB",
              watched: true,
              monitored: true,
            },
            {
              episodeNumber: 2,
              title: "Chapter Two: The Weirdo on Maple Street",
              airDate: "2016-07-15",
              downloadStatus: "downloaded",
              hasSubtitles: true,
              subtitleLanguages: ["English", "French"],
              fileSize: "3.1 GB",
              watched: true,
              monitored: true,
            },
            {
              episodeNumber: 3,
              title: "Chapter Three: Holly, Jolly",
              airDate: "2016-07-15",
              downloadStatus: "downloading",
              hasSubtitles: false,
              subtitleLanguages: [],
              fileSize: "3.0 GB",
              watched: false,
              monitored: true,
            },
          ],
        },
      ],
    },
  };

  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 500));

  // Return mock data based on ID
  return mockMovies?.[id] || mockTVShows?.[id] || null;
};
